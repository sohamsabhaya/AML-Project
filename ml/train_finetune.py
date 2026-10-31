"""Two-stage fine-tuning of ResNet50 (optionally EfficientNetV2-S).

STATUS: NOT YET RUN. Requires TensorFlow >= 2.16, the dataset, and ideally a GPU
(see ml/Brain_Tumor_Finetune_Colab.ipynb). No result from this script is claimed.

Plan
  Stage 1: backbone frozen, train the new head only (lr STAGE1_LR).
  Stage 2: unfreeze the last block group (conv5, or conv4+conv5) with a low
           learning rate; every BatchNormalization layer stays frozen so the small
           batch statistics of this dataset do not disturb the pretrained ones.
  Regularisation: mild augmentation (flip, small rotation/zoom/contrast), label
  smoothing, dropout, early stopping, checkpoint on validation loss.
  Validation data comes from the duplicate-aware manifests written by data_audit.py.
  The test set is never used for any decision here.

Preprocessing is part of the saved model (like the original notebook), so inference
code feeds raw RGB in [0, 255]:
  resnet50        -> keras.applications.resnet50.preprocess_input
  efficientnetv2s -> built-in (include_preprocessing=True, expects [0, 255])

Usage:
  python ml/train_finetune.py --model resnet50 --unfreeze conv5 --seed 42
  python ml/train_finetune.py --model efficientnetv2s --seed 42
"""
import argparse
import json
import random
from pathlib import Path

import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

import config


def set_seed(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    tf.random.set_seed(seed)


def make_dataset(manifest: Path, data_dir: Path, batch_size: int, training: bool, seed: int):
    """tf.data pipeline from a manifest CSV (columns: path, label)."""
    df = pd.read_csv(manifest)
    paths = [str(data_dir / p) for p in df["path"]]
    labels = df["label"].map({c: i for i, c in enumerate(config.CLASSES)}).astype("int32").tolist()
    ds = tf.data.Dataset.from_tensor_slices((paths, labels))
    if training:
        ds = ds.shuffle(len(paths), seed=seed, reshuffle_each_iteration=True)

    def load(path, label):
        img = tf.io.decode_image(tf.io.read_file(path), channels=3, expand_animations=False)
        img = tf.image.resize(img, config.IMG_SIZE)  # float32, values stay in [0, 255]
        img.set_shape((*config.IMG_SIZE, 3))
        return img, label

    ds = ds.map(load, num_parallel_calls=tf.data.AUTOTUNE)
    return ds.batch(batch_size).prefetch(tf.data.AUTOTUNE)


def augmentation():
    """Mild augmentation: MRI slices are roughly left/right symmetric; avoid strong warps."""
    return keras.Sequential([
        layers.RandomFlip("horizontal"),
        layers.RandomRotation(0.04),   # about +-14 degrees
        layers.RandomZoom(0.1),
        layers.RandomContrast(0.1),
    ], name="augmentation")


def build_model(name: str):
    """Returns (model, backbone). Input is raw RGB in [0, 255]."""
    inputs = layers.Input(shape=(*config.IMG_SIZE, 3))
    x = augmentation()(inputs)
    if name == "resnet50":
        x = layers.Lambda(keras.applications.resnet50.preprocess_input, name="resnet_preprocess")(x)
        backbone = keras.applications.ResNet50(weights="imagenet", include_top=False,
                                               input_shape=(*config.IMG_SIZE, 3))
    elif name == "efficientnetv2s":
        # Keras EfficientNetV2 includes its own rescaling layer; do NOT preprocess twice.
        backbone = keras.applications.EfficientNetV2S(weights="imagenet", include_top=False,
                                                      input_shape=(*config.IMG_SIZE, 3),
                                                      include_preprocessing=True)
    else:
        raise ValueError(name)
    backbone.trainable = False
    x = backbone(x, training=False)  # keeps BatchNorm in inference mode
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(config.DROPOUT)(x)
    x = layers.Dense(128, activation="relu")(x)
    x = layers.Dropout(config.DROPOUT)(x)
    outputs = layers.Dense(len(config.CLASSES), activation="softmax")(x)
    return keras.Model(inputs, outputs, name=f"{name}_finetune"), backbone


def unfreeze(backbone, name: str, depth: str):
    """Unfreeze trailing layers but keep every BatchNormalization frozen."""
    backbone.trainable = True
    if name == "resnet50":
        start = config.UNFREEZE_FROM[depth]
        names = [l.name for l in backbone.layers]
        if start not in names:
            raise ValueError(f"Layer {start} not found in ResNet50")
        cut = names.index(start)
    else:  # EfficientNetV2-S: unfreeze the last ~third of the layers
        cut = int(len(backbone.layers) * 0.66)
    for i, layer in enumerate(backbone.layers):
        layer.trainable = i >= cut and not isinstance(layer, layers.BatchNormalization)


def smoothed_loss(num_classes: int, eps: float):
    """Label smoothing for integer labels (Keras sparse loss has no smoothing arg)."""
    def loss(y_true, y_pred):
        y = tf.one_hot(tf.cast(tf.reshape(y_true, [-1]), tf.int32), num_classes)
        return keras.losses.categorical_crossentropy(y, y_pred, label_smoothing=eps)
    loss.__name__ = "smoothed_sparse_ce"
    return loss


def callbacks(ckpt_path: Path):
    return [
        keras.callbacks.ModelCheckpoint(str(ckpt_path), monitor="val_loss", save_best_only=True, verbose=1),
        keras.callbacks.EarlyStopping(monitor="val_loss", patience=config.EARLY_STOP_PATIENCE,
                                      restore_best_weights=True, verbose=1),
        keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.3, patience=2, verbose=1),
    ]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", choices=["resnet50", "efficientnetv2s"], default="resnet50")
    ap.add_argument("--unfreeze", choices=["conv5", "conv4"], default="conv5",
                    help="ResNet50 only: conv5 = last block group, conv4 = last two")
    ap.add_argument("--seed", type=int, default=config.SEEDS[0])
    ap.add_argument("--data-dir", default=str(config.DATA_DIR))
    ap.add_argument("--split-dir", default=str(config.SPLIT_DIR))
    ap.add_argument("--out-dir", default=str(config.CKPT_DIR))
    ap.add_argument("--stage1-epochs", type=int, default=config.STAGE1_EPOCHS)
    ap.add_argument("--stage2-epochs", type=int, default=config.STAGE2_EPOCHS)
    ap.add_argument("--skip-stage2", action="store_true", help="head-only baseline (experiment E1)")
    args = ap.parse_args()

    set_seed(args.seed)
    data_dir, split_dir, out_dir = Path(args.data_dir), Path(args.split_dir), Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tag = f"{args.model}_{args.unfreeze if args.model == 'resnet50' else 'last3rd'}_seed{args.seed}"
    ckpt = out_dir / f"{tag}.keras"

    train_ds = make_dataset(split_dir / "train.csv", data_dir, config.BATCH_SIZE, True, args.seed)
    val_ds = make_dataset(split_dir / "val.csv", data_dir, config.BATCH_SIZE, False, args.seed)

    model, backbone = build_model(args.model)
    loss = smoothed_loss(len(config.CLASSES), config.LABEL_SMOOTHING)
    history = {}

    # Stage 1: head only
    model.compile(optimizer=keras.optimizers.Adam(config.STAGE1_LR), loss=loss, metrics=["accuracy"])
    h1 = model.fit(train_ds, validation_data=val_ds, epochs=args.stage1_epochs, callbacks=callbacks(ckpt))
    history["stage1"] = {k: [float(v) for v in vs] for k, vs in h1.history.items()}

    # Stage 2: partial unfreeze, low LR, BatchNorm frozen
    if not args.skip_stage2:
        unfreeze(backbone, args.model, args.unfreeze)
        model.compile(optimizer=keras.optimizers.Adam(config.STAGE2_LR), loss=loss, metrics=["accuracy"])
        n_train = sum(int(np.prod(v.shape)) for v in model.trainable_variables)
        print(f"Stage 2 trainable parameters: {n_train:,}")
        h2 = model.fit(train_ds, validation_data=val_ds, epochs=args.stage2_epochs, callbacks=callbacks(ckpt))
        history["stage2"] = {k: [float(v) for v in vs] for k, vs in h2.history.items()}

    # Final model = best val-loss weights (restore_best_weights); save once more for safety.
    model.save(ckpt)
    (out_dir / f"{tag}_history.json").write_text(json.dumps(
        {"args": vars(args), "label_smoothing": config.LABEL_SMOOTHING, "history": history}, indent=2))
    print(f"Saved {ckpt}. Evaluate on the test set with ml/evaluate.py (the only place the test set is used).")


if __name__ == "__main__":
    main()
