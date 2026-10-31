# Methodology

All numbers below come from the notebook's saved outputs and `model_comparison_results.csv`. Where something could not be read from those outputs it is stated as unknown rather than estimated.

## 1. Problem statement

Given a single 2-D brain MRI slice, predict one of four classes: glioma, meningioma, pituitary tumor, or no tumor. This is a supervised multi-class image classification task. The project is an educational prototype: the aim is to compare a small custom CNN against transfer learning from ResNet50 and to wrap the better model in a safe, explainable web interface. It is not a diagnostic tool (see `ETHICS_AND_PRIVACY.md`).

## 2. Dataset

Source: the Kaggle "Brain Tumor MRI Dataset" by Nickparvar (2021), which builds on the figshare brain tumor collection of Cheng et al. (2015).

Properties as audited in notebook cells 4, 6 and 12:

| Property | Value |
|---|---|
| Classes | glioma, meningioma, notumor, pituitary |
| Training folder | 5,600 images (1,400 per class) |
| Testing folder | 1,600 images (400 per class) |
| Class balance | exactly 25% per class in both folders |
| Corrupted or unreadable files | 0 in Training, 0 in Testing |
| Identical images across Training and Testing | 0 (hash comparison) |
| Identical images inside Training | 138 hashes with 171 duplicate copies |
| Input size used | 224 x 224, 3 channels |

Notes and caveats:

- The documentation uses the notebook's counts (1,400 and 400 per class), since those are what the models were evaluated on; the ML owner should confirm the provenance of this exactly balanced copy of the dataset.
- The notebook's own note says the repeated slices inside Training were kept "as part of acquisition sequences". Because the validation split is carved out of Training, duplicates can land on both sides of the split (see section 9).
- The dataset is not stored in the repository (`dataset/` is git-ignored). Download it from Kaggle to reproduce training.

## 3. Preprocessing

- Images are loaded with `image_dataset_from_directory` at 224 x 224 with integer labels (class order is alphabetical: glioma, meningioma, notumor, pituitary).
- Both saved models embed their own preprocessing, so the input is raw RGB with values 0-255:
  - Custom CNN: a `Rescaling(1/255)` layer.
  - ResNet50: a `Lambda` layer calling `keras.applications.resnet50.preprocess_input`.
- Augmentation lives inside the models (random horizontal flip is present in the saved files and is inactive at inference; the project README also lists rotation and zoom for the training pipeline).
- The web backend reproduces only the loading step: convert to RGB, resize to 224 x 224, no scaling. Dividing by 255 again would double-normalise, which is why the backend deliberately does not.

## 4. Models

| | Custom CNN (baseline) | ResNet50 transfer model |
|---|---|---|
| Structure | 3 blocks of Conv2D (32, 64, 128 filters, 3x3) + BatchNorm + MaxPool, then GlobalAveragePooling, Dense(128), Dropout(0.4), Dense(4, softmax) | ImageNet-pretrained ResNet50 without top, frozen, then GlobalAveragePooling, Dense(128), BatchNorm, Dropout(0.4), Dense(4, softmax) |
| Total parameters | 111,172 | 23,851,012 |
| Trainable parameters | 110,724 | 263,044 |
| Optimizer, learning rate | Adam, 1e-3 | Adam, 1e-4 |
| Loss | sparse categorical cross-entropy | sparse categorical cross-entropy |

The ResNet50 backbone is frozen: only the new head (263,044 parameters) is trained, no fine-tuning of the backbone was done.

## 5. Training protocol

- The Training folder is split 80/20 into 4,480 training and 1,120 validation images (notebook cell 12). The split is deterministic but random at image level, not stratified by patient.
- Up to 15 epochs, batch size consistent with 140 steps per epoch.
- Callbacks for both models: EarlyStopping on validation loss (patience 4, restore best weights) and ReduceLROnPlateau (factor 0.2, patience 2, minimum 1e-6).
- ResNet50: validation accuracy rose steadily from 85.09% (epoch 1) to 95.80% (epoch 15), with best weights restored from epoch 15.
- Custom CNN: the saved output of the notebook is truncated after epoch 8, and the validation accuracy was very unstable in the early epochs (25.45% at epoch 1, 82.59% at epoch 7). The full curve cannot be reproduced from the saved output, so no final training figure is cited here.
- Validation accuracy is optimistic because of duplicates inside Training (section 9). The test figures below are the ones to rely on.

## 6. Evaluation protocol

Both models are evaluated once on the untouched Testing folder (1,600 images, 400 per class). Reported metrics are test accuracy and macro-averaged precision, recall and F1. The notebook also draws confusion matrices, a per-class classification report and one-vs-rest ROC curves. The per-class report is printed text; the confusion matrices and ROC AUC values were read from the saved figures and cross-checked (rows sum to 400), and are stored in `ml/results/model_insights.json`. For ResNet50 the notebook reports 1,440 correct and 160 misclassified out of 1,600.

## 7. Results

| Metric (test, n = 1,600) | Custom CNN | ResNet50 |
|---|---|---|
| Accuracy | 74.31% | 90.00% |
| Macro precision | 75.81% | 90.61% |
| Macro recall | 74.31% | 90.00% |
| Macro F1 | 70.55% | 89.75% |
| Total parameters | 111,172 | 23,851,012 |
| Trainable parameters | 110,724 | 263,044 |

Per class (test, from `ml/results/model_insights.json`): ResNet50 glioma recall is 0.71 (87 of 400 gliomas predicted as meningioma) and meningioma precision is 0.79; the custom CNN's meningioma recall is only 0.25 (it mostly answers glioma or notumor). Both models have notumor recall of 1.00 (the custom CNN's notumor precision is only 0.68). Macro recall equals accuracy because the test classes are exactly balanced. ResNet50 is better on every metric, by about 15.7 percentage points of accuracy, but there is no confidence interval: a single training run and a single test set were used. With n = 1,600 the sampling uncertainty of a 90% accuracy is roughly plus or minus 1.5 percentage points (binomial standard error about 0.75 points), which is a back-of-the-envelope estimate, not a result from the notebook.

## 8. Grad-CAM

Grad-CAM (Selvaraju et al., 2017) weights the feature maps of the last convolutional layer by the average gradient of the predicted class score, sums them, applies ReLU, normalises and overlays the result on the image. The backend uses layer `conv5_block3_out` (7 x 7 x 2048) for ResNet50 and `conv2d_2` (28 x 28 x 128) for the custom CNN, with a fallback to the last layer with a 4-D output. The heatmap shows which regions influenced the model's score; it does not prove the model "looked at the tumor", and it is coarse (7 x 7 for ResNet50). It is an explanation aid, not a localisation result, and it has not been validated against expert annotation.

## 9. Threats to validity

1. Duplicates and leakage inside Training: 138 hashes with 171 extra copies. No duplicates between Training and Testing were found by exact hash, so the test score is not inflated by exact copies, but near-duplicates (neighbouring slices, re-encoded images) are not detected by exact hashing. The validation score is optimistic because duplicates can fall on both sides of the 80/20 split.
2. Patient-level split unknown: the dataset provides no patient identifiers in the folders, so slices from one patient may appear in both Training and Testing. If so, the test accuracy overestimates generalisation to new patients.
3. Single-source data: the images come from one public collection (with the figshare collection as its origin). Scanner, protocol and site variation are not represented.
4. No external validation: the models have not been tested on any dataset from another source.
5. Uncalibrated softmax: the displayed confidence is a softmax score, not a probability of being correct. The notebook itself says so. The app's 0.6 uncertain threshold is a pragmatic choice, not a calibrated operating point.
6. Class-balanced data unlike real prevalence: the test set is 25% per class; in practice the class mix differs, so precision in deployment would differ from the reported precision.
7. Frozen backbone, single run, no hyper-parameter search, no confidence intervals or repeated seeds.
8. 2-D slices only; the task is easier than reading a full 3-D study.

## 10. Planned improvement experiments (not done yet)

All items below are planned, not completed, and no result is claimed for them.

- De-duplicate Training (exact and perceptual hashing) and re-split before creating the validation set.
- Group the split by patient if identifiers can be recovered; otherwise state that it cannot.
- Fine-tune the top ResNet50 blocks with a low learning rate; compare with the frozen baseline.
- Repeat training with several seeds and report mean and spread.
- Temperature scaling on a clean validation set, then reliability diagrams and expected calibration error.
- Per-class precision, recall and confusion matrices are now saved in `ml/results/model_insights.json` (done). Still missing: bootstrap confidence intervals and calibration numbers.
- `ml/` contains a written but never executed improvement pipeline (duplicate-aware split, fine-tuning, evaluation with bootstrap CIs and temperature scaling). No result from it is claimed.
- Evaluate on an external dataset if one with the same four classes is available.
- Compare against another backbone such as EfficientNet (only as an experiment, no claim in advance).

## 11. References

1. Nickparvar, M. "Brain Tumor MRI Dataset", Kaggle (2021). https://www.kaggle.com/datasets/masoudnickparvar/brain-tumor-mri-dataset
2. Cheng, J. et al. Brain tumor dataset, figshare (2015). The source collection on which the Kaggle dataset builds.
3. He, K., Zhang, X., Ren, S., Sun, J. "Deep Residual Learning for Image Recognition", CVPR 2016.
4. Selvaraju, R. R. et al. "Grad-CAM: Visual Explanations from Deep Networks via Gradient-based Localization", ICCV 2017.
5. Chollet, F. et al. Keras (2015). https://keras.io
6. Abadi, M. et al. TensorFlow: Large-scale machine learning on heterogeneous systems (2015). https://www.tensorflow.org
