# Experiment log

**NOT YET RUN: no results claimed.** All result cells are empty on purpose. Fill them only from completed runs (copy from `outputs/eval/<name>/metrics.json`) and record the date, seed and commit.

Baseline for reference (already in the notebook, cell 28, original random validation split, single run): ResNet50 frozen backbone, test accuracy 90.00%, macro F1 89.75%; custom CNN 74.31% / 70.55%.

## Planned experiments

| ID | Question | Setup | Status |
|---|---|---|---|
| E1 | What does the frozen-backbone ResNet50 give on the duplicate-aware split? | `--skip-stage2`, seeds 42/1337/2024 | not run |
| E2 | Does unfreezing conv5 (BatchNorm frozen, lr 1e-5) help? | two-stage, `--unfreeze conv5` | not run |
| E3 | Does also unfreezing conv4 help or overfit? | two-stage, `--unfreeze conv4` | not run |
| E4 | Effect of label smoothing and mild augmentation | E2 with `LABEL_SMOOTHING=0` / flip-only augmentation | not run |
| E5 | Is EfficientNetV2-S better than ResNet50? | `--model efficientnetv2s` | not run |
| E6 | Is the best model calibrated; does temperature scaling help? | `evaluate.py` on the best checkpoint | not run |

## Results (test set, 1,600 images)

| ID | Seed | Accuracy | 95% CI | Macro F1 | Glioma recall | Meningioma precision | Macro AUC | ECE before | ECE after T | Date | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 | 42 | | | | | | | | | | |
| E1 | 1337 | | | | | | | | | | |
| E1 | 2024 | | | | | | | | | | |
| E2 | 42 | | | | | | | | | | |
| E2 | 1337 | | | | | | | | | | |
| E2 | 2024 | | | | | | | | | | |
| E3 | 42 | | | | | | | | | | |
| E3 | 1337 | | | | | | | | | | |
| E3 | 2024 | | | | | | | | | | |
| E4 | 42 | | | | | | | | | | |
| E5 | 42 | | | | | | | | | | |
| E6 | 42 | | | | | | | | | | |

## Data audit (from `outputs/splits/audit_report.json`)

| Item | Value |
|---|---|
| Exact duplicate hashes in Training | |
| Near-duplicate pairs train vs test (Hamming <= 4) | |
| Train / validation size after grouped split | |

## Validation vs test gap

| ID | Best val accuracy | Test accuracy | Gap |
|---|---|---|---|
| E1 | | | |
| E2 | | | |

## Observations
(Write only what the numbers above support, including negative results.)
