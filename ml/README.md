# ml/ : planned improvement pipeline

**Status: NOT YET RUN. No result from this folder is claimed.** Everything here was written but not executed (no GPU, no dataset in the repository). The only real, verified numbers in the project are the ones from the original notebook, listed with their cell numbers in `results/existing_results.md` and exposed to the web app in `results/model_insights.json`.

Educational project, not a medical device.

## Purpose

The original notebook (`../Brain_Tumor_Classification_AML.ipynb`) reaches 90.00% test accuracy with a frozen ResNet50. Its known weaknesses: the validation split is random per file while Training holds 138 duplicate hashes (171 copies), the backbone is frozen and still improving at epoch 15, glioma recall is 0.71, there is a single run with no confidence intervals, and softmax scores are not calibrated. This pipeline addresses those points:

| File | Role |
|---|---|
| `config.py` | paths (no absolute paths; `BRAIN_DATA_DIR`, `BRAIN_OUT_DIR`), seeds, hyper-parameters |
| `data_audit.py` | exact and near-duplicate detection, duplicate-aware train/validation split, manifests |
| `train_finetune.py` | two-stage ResNet50 fine-tuning (optional EfficientNetV2-S) |
| `evaluate.py` | accuracy, per-class P/R/F1, confusion matrix, one-vs-rest AUC, bootstrap CIs, ECE and temperature scaling, error list, Grad-CAM galleries |
| `Brain_Tumor_Finetune_Colab.ipynb` | cells that call the scripts (unexecuted) |
| `EXPERIMENT_LOG.md` | planned experiments E1-E6 with empty result tables |
| `results/` | numbers extracted from the existing notebook (verified) |

## Dataset layout expected

The Kaggle dataset (Masoud Nickparvar, "Brain Tumor MRI Dataset") is not included and is not downloaded by any script. Place it at `dataset/` in the repository root (or point `BRAIN_DATA_DIR` at it):

```text
dataset/Training/{glioma,meningioma,notumor,pituitary}/*.jpg
dataset/Testing/{glioma,meningioma,notumor,pituitary}/*.jpg
```

The notebook's copy has 1,400 training and 400 test images per class (5,600 / 1,600). Check the dataset page for its current license.

## How to run

### Colab (recommended, GPU)
Open `Brain_Tumor_Finetune_Colab.ipynb`, set the runtime to GPU, upload the dataset, and run the cells top to bottom.

### Locally
```bash
pip install -r ml/requirements-ml.txt
python ml/data_audit.py                                   # writes ml/outputs/splits/*.csv
python ml/train_finetune.py --model resnet50 --unfreeze conv5 --seed 42
python ml/evaluate.py --model ml/outputs/checkpoints/resnet50_conv5_seed42.keras
```
The test set is read only by `evaluate.py`. Temperature scaling is fitted on the validation manifest.

## Planned experiments (results empty on purpose)

| ID | Planned experiment | Accuracy | Macro F1 | Glioma recall | ECE |
|---|---|---|---|---|---|
| E1 | Frozen ResNet50 on the duplicate-aware split (3 seeds) | | | | |
| E2 | Unfreeze conv5, BatchNorm frozen, lr 1e-5 (3 seeds) | | | | |
| E3 | Unfreeze conv4 + conv5 | | | | |
| E4 | Label smoothing and augmentation ablation | | | | |
| E5 | EfficientNetV2-S | | | | |
| E6 | Calibration with temperature scaling on the best model | | | | |

## Notes and caveats
* Bootstrap intervals only capture test-set sampling noise; train several seeds to see run-to-run variance.
* Grad-CAM shows where the network looked, not that it is right.
* A better score on this dataset would not show the model works on scans from other hospitals; no external validation is planned within this repository.
* Models saved by `train_finetune.py` nest the backbone as one layer; `evaluate.py` handles this. The backend Grad-CAM code looks layers up recursively, but check it before swapping models in.
* Model files and `outputs/` should not be committed (large).
