# Existing results (extracted from the saved notebook outputs)

Source: `Brain_Tumor_Classification_AML.ipynb` (34 cells, 0-based numbering, as stored in the file). Nothing here was re-run. The notebook, the `.keras` files and the CSV were only read.

Text outputs are quoted exactly. Items marked **(figure)** exist only as an image saved in the notebook and were read off that image; they were cross-checked arithmetically against the printed text.

## 1. Numbers and where they come from

| Quantity | Value | Cell | Exact output text / evidence |
|---|---|---|---|
| Classes | glioma, meningioma, notumor, pituitary | 4 | `Detected Diagnostic Classes (4): ['glioma', 'meningioma', 'notumor', 'pituitary']` |
| Training images per class | 1400 each (5600 total) | 6, 12 | table row `glioma 1400 400 1800 25.0` (same for other classes); `Found 5600 files belonging to 4 classes.` |
| Test images per class | 400 each (1600 total) | 6, 12 | `Found 1600 files belonging to 4 classes.` |
| Train / validation split | 4480 / 1120 | 12 | `Using 4480 files for training.` / `Using 1120 files for validation.` |
| Unreadable files | 0 train, 0 test | 6 | `Corrupted or Unreadable Files in Training Set: 0` / `... Testing Set:  0` |
| Train/test exact duplicates | 0 | 6 | `Cross-Split Duplicate Images (Leakage):       0` |
| Duplicates inside Training | 138 hashes, 171 extra copies | 6 | `Intra-Training Identical Slices:              138 hashes (171 duplicate copies)` |
| Image size, batch size | 224x224, 32 | 12 | `IMG_SIZE = (224, 224)`, `BATCH_SIZE = 32` (code) |
| Augmentation | RandomFlip("horizontal") only | 12 | `data_augmentation = keras.Sequential([layers.RandomFlip("horizontal"),])` (code) |
| Custom CNN params | total 111,172; trainable 110,724; non-trainable 448 | 14 | `Total params: 111,172 (434.27 KB)`, `Trainable params: 110,724 (432.52 KB)`, `Non-trainable params: 448 (1.75 KB)` |
| ResNet50 params | total 23,851,012; trainable 263,044; non-trainable 23,587,968 | 16 | `Total params: 23,851,012 (90.98 MB)`, `Trainable params: 263,044 (1.00 MB)`, `Non-trainable params: 23,587,968 (89.98 MB)` |
| ResNet50 optimiser | Adam, lr 1e-4, backbone frozen | 16 | `base_model.trainable = False`, `learning_rate=1e-4` (code) |
| Custom CNN optimiser | Adam, lr 1e-3 | 14 | `learning_rate=1e-3` (code) |
| Callbacks (both) | EarlyStopping(val_loss, patience 4, restore best), ReduceLROnPlateau(0.2, patience 2) | 18, 20 | code |
| Custom CNN training log | epochs 1-7 recorded; val_accuracy 0.2545, 0.4161, 0.4759, 0.3107, 0.5696, 0.6714, 0.8259; log stops mid epoch 8 (`43/140`) | 18 | e.g. `Epoch 7/15 ... accuracy: 0.8614 - loss: 0.3718 - val_accuracy: 0.8259 - val_loss: 0.4011 - learning_rate: 2.0000e-04`. The message `Custom CNN successfully trained and saved` is not in the saved output. |
| ResNet50 training log | 15 epochs; epoch 15 val_accuracy 0.9580, val_loss 0.1293, train accuracy 0.9574 | 20 | `Epoch 15/15 ... accuracy: 0.9574 - loss: 0.1272 - val_accuracy: 0.9580 - val_loss: 0.1293 - learning_rate: 1.0000e-04` and `Restoring model weights from the end of the best epoch: 15.` Validation loss fell at nearly every epoch (epoch 11 was the only rise), so training had not converged. |
| Test accuracy | CNN 74.31%, ResNet50 90.00% | 28 | table rows `0 Test Accuracy 74.31% 90.00%` |
| Macro precision | 75.81% / 90.61% | 28 | `1 Macro Precision 75.81% 90.61%` |
| Macro recall | 74.31% / 90.00% | 28 | `2 Macro Recall 74.31% 90.00%` |
| Macro F1 | 70.55% / 89.75% | 28 | `3 Macro F1-Score 70.55% 89.75%` |
| ResNet50 correct / wrong | 1440 / 160 | 30 | `Total Test Samples: 1600 | Correct: 1440 | Misclassified: 160` |

### Per-class report, Custom CNN (cell 24, `CLASSIFICATION REPORT: CUSTOM CNN BASELINE`)

| class | precision | recall | f1-score | support |
|---|---|---|---|---|
| glioma | 0.69 | 0.76 | 0.72 | 400 |
| meningioma | 0.80 | 0.25 | 0.38 | 400 |
| notumor | 0.68 | 1.00 | 0.81 | 400 |
| pituitary | 0.87 | 0.97 | 0.91 | 400 |
| accuracy | | | 0.74 | 1600 |
| macro avg | 0.76 | 0.74 | 0.71 | 1600 |

### Per-class report, ResNet50 (cell 24, `CLASSIFICATION REPORT: RESNET50 TRANSFER MODEL`)

| class | precision | recall | f1-score | support |
|---|---|---|---|---|
| glioma | 0.95 | 0.71 | 0.81 | 400 |
| meningioma | 0.79 | 0.91 | 0.85 | 400 |
| notumor | 0.92 | 1.00 | 0.96 | 400 |
| pituitary | 0.96 | 0.98 | 0.97 | 400 |
| accuracy | | | 0.90 | 1600 |
| macro avg | 0.91 | 0.90 | 0.90 | 1600 |

### Confusion matrices (figure, cell 24; rows = true, columns = predicted, order glioma, meningioma, notumor, pituitary)

Custom CNN: `[[303,20,64,13],[129,99,125,47],[0,0,400,0],[7,5,1,387]]` (diagonal 1189 = 74.31% of 1600).
ResNet50: `[[285,87,24,4],[14,363,11,12],[0,1,399,0],[1,6,0,393]]` (diagonal 1440 = 90.00%).
Both match the printed precision and recall (for example ResNet50 glioma precision 285/300 = 0.95, recall 285/400 = 0.71).

### One-vs-rest ROC AUC (figure legends, cell 26)

| class | Custom CNN | ResNet50 |
|---|---|---|
| glioma | 0.875 | 0.951 |
| meningioma | 0.895 | 0.969 |
| notumor | 0.980 | 0.999 |
| pituitary | 0.992 | 0.999 |

(An earlier audit said the notebook has no AUC numbers; they are in the plot legends but not in any text output.)

### Not in the notebook
Calibration (ECE), confidence intervals, Grad-CAM, repeated runs, external validation.

## 2. Discrepancies

README = the original root README.md before this rewrite.

| # | Claim | What the notebook / files show |
|---|---|---|
| 1 | README: custom CNN has "~150k parameters" | 111,172 (cell 14, cell 28, CSV). The notebook's own conclusion (cell 33) says "~111k". |
| 2 | README: augmentation is "random horizontal flip, rotation, zoom" | Cell 12 defines only `RandomFlip("horizontal")`. |
| 3 | README: Testing folder has 1,311 scans | 1,600 (400 per class), cells 6 and 12. 1,311 is the size of the original Kaggle test folder; this project's folder is a different, balanced 4 x 400 set. Training 5,600 in the README is correct. |
| 4 | README: "in-memory caching" (and code comment "Apply Memory Caching & Prefetching") | Cell 12 only calls `.prefetch(AUTOTUNE)`; there is no `.cache()`. |
| 5 | README: "[0,255] -> [0,1] normalization" as a general step | True only for the custom CNN (`Rescaling(1/255)`). ResNet50 uses `Lambda(resnet50.preprocess_input)` (caffe-style mean subtraction, BGR), confirmed in the `.keras` config.json. |
| 6 | README: "academic-grade", "Clinical Evaluation", "Clinical CAD" | The notebook itself (cell 32) says it is "an educational research prototype and is NOT a certified clinical diagnostic tool". No clinical evaluation was done. |
| 7 | README: "deterministic 80/20 split" | Seeded (seed=42), but the split is random per file, and the training folder contains 138 duplicate hashes (171 copies), so near-identical images can sit on both sides. Validation accuracy (ResNet50 0.9580) is therefore optimistic relative to the test accuracy (0.9000). Cell 6's note that duplicates "are retained as part of acquisition sequences" is an assumption, not something the output shows. |
| 8 | Notebook cell 33: "helped both models generalize well without overfitting" | Not supported for the CNN: validation accuracy swings 0.25 to 0.83 (cell 18) and test meningioma recall is 0.25. |
| 9 | README lists ROC/AUC and a "Clinical CAD inference simulation" | ROC curves exist (cell 26) and the single-image helper exists (cell 32). There is no Grad-CAM, calibration or confidence interval in the notebook; the Grad-CAM in the web app is separate code in `backend/`. |
| 10 | Custom CNN training log (cell 18) | The saved output ends mid epoch 8 with no early-stopping or final message. The model file and the test results exist, so the notebook was probably re-run or interrupted afterwards; the final CNN epoch and best epoch cannot be verified from the notebook. |
| 11 | CSV vs cell 28 | Identical for all 12 values. Fair note: the CSV rounds to two decimals in percent, so fractions in `model_insights.json` (0.7431 etc.) are exact conversions. |
| 12 | Cell 4 prints `d:\AI Project\...\dataset` and cell 2 a TensorFlow-on-Windows warning | Training was on Windows with no GPU for the CNN (about 125 s per epoch, cell 18); not a discrepancy, but the notebook is not directly reproducible without the dataset at `dataset/`. |
| 13 | Parameter and metric figures for the saved ResNet50 | The `.keras` config confirms the Lambda preprocess layer and the final layers `GlobalAveragePooling2D -> Dense -> BatchNormalization -> Dropout -> Dense`, consistent with cell 16. |
