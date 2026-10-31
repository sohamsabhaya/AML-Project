"""Test-set evaluation with uncertainty, calibration, error analysis and Grad-CAM.

STATUS: NOT YET RUN. Requires TensorFlow >= 2.16, scikit-learn, matplotlib and the
dataset. Works on any saved Keras model that takes raw RGB [0, 255] (the original
notebook models and the ones produced by train_finetune.py).

Outputs in --out-dir (default ml/outputs/eval/<model-name>/):
  metrics.json          accuracy, per-class P/R/F1, macro scores, OvR AUC,
                        bootstrap 95% CIs, ECE before/after temperature scaling
  confusion_matrix.csv  rows = true, columns = predicted (order: config.CLASSES)
  predictions.csv       one row per test image with probabilities
  misclassified.csv     the errors, most confident first
  gradcam_*.png         galleries of correct and wrong cases

Honesty notes
  * Temperature is fitted on the VALIDATION manifest, never on the test set.
  * Bootstrap resamples test images (2,000 draws by default); it captures sampling
    noise of the test set only, not run-to-run training variance (use several seeds).
  * Grad-CAM shows where the network looked; it is not evidence of correctness.

Usage:
  python ml/evaluate.py --model path/to/model.keras --name resnet50_finetune_seed42
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow import keras
from scipy.optimize import minimize_scalar
from sklearn.metrics import (accuracy_score, confusion_matrix,
                             precision_recall_fscore_support, roc_auc_score)
from sklearn.preprocessing import label_binarize

import config


# ---------------------------------------------------------------- data / inference
def load_images(paths, data_dir):
    imgs = []
    for p in paths:
        img = tf.io.decode_image(tf.io.read_file(str(data_dir / p)), channels=3, expand_animations=False)
        imgs.append(tf.image.resize(img, config.IMG_SIZE).numpy())
    return np.stack(imgs).astype("float32")


def predict_probs(model, paths, data_dir, batch=32):
    out = []
    for i in range(0, len(paths), batch):
        out.append(model.predict(load_images(paths[i:i + batch], data_dir), verbose=0))
    return np.concatenate(out)


def load_model(path):
    # Lambda layers (ResNet preprocess) need safe_mode=False; only load files you trust.
    return keras.models.load_model(path, compile=False, safe_mode=False)


# ---------------------------------------------------------------- metrics
def bootstrap_ci(y_true, y_pred, n_iter, seed=0):
    """95% percentile CI for accuracy and macro-F1 by resampling test images."""
    rng = np.random.default_rng(seed)
    n = len(y_true)
    accs, f1s = [], []
    for _ in range(n_iter):
        idx = rng.integers(0, n, n)
        accs.append(accuracy_score(y_true[idx], y_pred[idx]))
        f1s.append(precision_recall_fscore_support(y_true[idx], y_pred[idx], average="macro",
                                                   zero_division=0)[2])
    pct = lambda a: [float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))]
    return {"accuracy_ci95": pct(accs), "macro_f1_ci95": pct(f1s), "iterations": n_iter}


def expected_calibration_error(probs, y_true, n_bins):
    """ECE: weighted mean |accuracy - confidence| over equal-width confidence bins."""
    conf = probs.max(axis=1)
    pred = probs.argmax(axis=1)
    correct = (pred == y_true).astype(float)
    edges = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf > lo) & (conf <= hi)
        if m.any():
            ece += m.mean() * abs(correct[m].mean() - conf[m].mean())
    return float(ece)


def fit_temperature(logits_like, y_true):
    """Single scalar T minimising NLL of softmax(log(p)/T) on validation data."""
    log_p = np.log(np.clip(logits_like, 1e-12, 1.0))

    def nll(t):
        z = log_p / t
        z = z - z.max(axis=1, keepdims=True)
        lp = z - np.log(np.exp(z).sum(axis=1, keepdims=True))
        return -lp[np.arange(len(y_true)), y_true].mean()

    return float(minimize_scalar(nll, bounds=(0.05, 10.0), method="bounded").x)


def apply_temperature(probs, t):
    z = np.log(np.clip(probs, 1e-12, 1.0)) / t
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


# ---------------------------------------------------------------- Grad-CAM
def find_last_conv_name(model):
    """Last 4-D feature map layer; searches inside a nested backbone if present."""
    best = None
    for layer in model.layers:
        if isinstance(layer, keras.Model):  # nested backbone
            for sub in layer.layers:
                if len(sub.output.shape) == 4:
                    best = (layer, sub.name)
        elif len(layer.output.shape) == 4 and "conv" in layer.name:
            best = (None, layer.name)
    return best


def gradcam(model, img, class_idx, conv_owner, conv_name):
    """Standard Grad-CAM for one image (raw RGB [0,255], shape HxWx3)."""
    if conv_owner is None:
        conv_out = model.get_layer(conv_name).output
        grad_model = keras.Model(model.inputs, [conv_out, model.output])
    else:  # backbone is a nested model: rebuild a path through it
        inner = keras.Model(conv_owner.inputs, [conv_owner.get_layer(conv_name).output, conv_owner.output])
        x = model.inputs[0]
        for layer in model.layers[1:]:
            if layer is conv_owner:
                conv_out, x = inner(x)
                break
            x = layer(x)
        started = False
        for layer in model.layers:
            if layer is conv_owner:
                started = True
                continue
            if started:
                x = layer(x)
        grad_model = keras.Model(model.inputs, [conv_out, x])
    with tf.GradientTape() as tape:
        conv_val, preds = grad_model(img[None], training=False)
        score = preds[:, class_idx]
    grads = tape.gradient(score, conv_val)
    weights = tf.reduce_mean(grads, axis=(1, 2))
    cam = tf.nn.relu(tf.reduce_sum(conv_val * weights[:, None, None, :], axis=-1))[0].numpy()
    cam = cam / (cam.max() + 1e-8)
    return tf.image.resize(cam[..., None], config.IMG_SIZE).numpy()[..., 0]


def save_gallery(model, df, probs, data_dir, out_path, title, max_n=8):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    found = find_last_conv_name(model)
    if found is None or df.empty:
        print(f"Skipping gallery {title}: no conv layer or no samples")
        return
    owner, name = found
    sel = df.head(max_n)
    fig, axes = plt.subplots(2, len(sel), figsize=(2.6 * len(sel), 5.4), squeeze=False)
    for k, (i, row) in enumerate(sel.iterrows()):
        img = load_images([row["path"]], data_dir)[0]
        pred = int(row["pred"])
        cam = gradcam(model, img, pred, owner, name)
        axes[0, k].imshow(img.astype("uint8"))
        axes[0, k].set_title(f"true {config.CLASSES[int(row['true'])]}\npred {config.CLASSES[pred]} "
                             f"({probs[i, pred]:.2f})", fontsize=8)
        axes[1, k].imshow(img.astype("uint8"))
        axes[1, k].imshow(cam, cmap="jet", alpha=0.4)
        for a in axes[:, k]:
            a.axis("off")
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True, help="path to a .keras model")
    ap.add_argument("--name", default=None, help="label for the output folder")
    ap.add_argument("--data-dir", default=str(config.DATA_DIR))
    ap.add_argument("--split-dir", default=str(config.SPLIT_DIR))
    ap.add_argument("--out-dir", default=str(config.EVAL_DIR))
    ap.add_argument("--bootstrap", type=int, default=config.BOOTSTRAP_ITERS)
    ap.add_argument("--no-gradcam", action="store_true")
    args = ap.parse_args()

    data_dir, split_dir = Path(args.data_dir), Path(args.split_dir)
    name = args.name or Path(args.model).stem
    out = Path(args.out_dir) / name
    out.mkdir(parents=True, exist_ok=True)

    model = load_model(args.model)
    cls_to_i = {c: i for i, c in enumerate(config.CLASSES)}

    test = pd.read_csv(split_dir / "test.csv")
    y = test["label"].map(cls_to_i).to_numpy()
    probs = predict_probs(model, test["path"].tolist(), data_dir)
    pred = probs.argmax(axis=1)

    # core metrics
    p, r, f, s = precision_recall_fscore_support(y, pred, labels=range(4), zero_division=0)
    mp, mr, mf, _ = precision_recall_fscore_support(y, pred, average="macro", zero_division=0)
    y_bin = label_binarize(y, classes=range(4))
    auc = {c: float(roc_auc_score(y_bin[:, i], probs[:, i])) for i, c in enumerate(config.CLASSES)}
    cm = confusion_matrix(y, pred, labels=range(4))

    # calibration: fit T on validation, report on test
    val = pd.read_csv(split_dir / "val.csv")
    yv = val["label"].map(cls_to_i).to_numpy()
    pv = predict_probs(model, val["path"].tolist(), data_dir)
    temp = fit_temperature(pv, yv)
    probs_cal = apply_temperature(probs, temp)

    metrics = {
        "model": args.model, "n_test": int(len(y)),
        "accuracy": float(accuracy_score(y, pred)),
        "macro_precision": float(mp), "macro_recall": float(mr), "macro_f1": float(mf),
        "per_class": [{"class": c, "precision": float(p[i]), "recall": float(r[i]),
                       "f1": float(f[i]), "support": int(s[i]), "roc_auc_ovr": auc[c]}
                      for i, c in enumerate(config.CLASSES)],
        "macro_auc_ovr": float(np.mean(list(auc.values()))),
        "bootstrap": bootstrap_ci(y, pred, args.bootstrap),
        "calibration": {
            "bins": config.CALIBRATION_BINS,
            "ece_before": expected_calibration_error(probs, y, config.CALIBRATION_BINS),
            "temperature_fitted_on_validation": temp,
            "ece_after_temperature": expected_calibration_error(probs_cal, y, config.CALIBRATION_BINS),
        },
    }
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2))
    pd.DataFrame(cm, index=config.CLASSES, columns=config.CLASSES).to_csv(out / "confusion_matrix.csv")

    # error analysis
    preds_df = test[["path", "label"]].copy()
    preds_df["true"], preds_df["pred"] = y, pred
    preds_df["pred_label"] = [config.CLASSES[i] for i in pred]
    preds_df["confidence"] = probs.max(axis=1)
    for i, c in enumerate(config.CLASSES):
        preds_df[f"p_{c}"] = probs[:, i]
    preds_df.to_csv(out / "predictions.csv", index=False)
    wrong = preds_df[preds_df["true"] != preds_df["pred"]].sort_values("confidence", ascending=False)
    wrong.to_csv(out / "misclassified.csv", index=False)
    print(json.dumps({k: metrics[k] for k in ("accuracy", "macro_f1", "macro_auc_ovr", "calibration")}, indent=2))
    print(f"{len(wrong)} misclassified of {len(y)}; see misclassified.csv")

    if not args.no_gradcam:
        right = preds_df[preds_df["true"] == preds_df["pred"]].sample(n=min(8, len(y)), random_state=0)
        save_gallery(model, right, probs, data_dir, out / "gradcam_correct.png", "Correct predictions")
        save_gallery(model, wrong, probs, data_dir, out / "gradcam_wrong.png",
                     "Most confident errors")


if __name__ == "__main__":
    main()
