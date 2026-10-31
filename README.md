# BrainScan AI: Brain Tumor MRI Multi-Class Classification
### Applied Machine Learning & Deep Learning course project

> **Not a medical device. Educational use only.** The models and the web application in this repository are a student project. They have not been clinically validated, must not be used to diagnose or treat anyone, and must not replace review by a qualified clinician. Do not upload real patient data to a shared machine.

This project builds and compares two deep learning pipelines that classify brain MRI slices into four categories, and wraps them in a small web application:
1. **Glioma:** tumors originating in glial cells, often aggressive with infiltrating margins.
2. **Meningioma:** tumors arising from the meningeal membranes, often slow-growing.
3. **Pituitary Tumor:** growths on the pituitary gland affecting the endocrine system and vision.
4. **No Tumor:** MRI slices with no tumor of these types.

---

## Project Overview and Methodology
All statements below refer to `Brain_Tumor_Classification_AML.ipynb` (cell numbers in brackets, counted from 0).
* **Data checks:** class balance, unreadable-file check (0 found) and an MD5 hash audit (cell 6). No identical images are shared between Training and Testing, but the Training folder contains 138 duplicate hashes (171 extra copies).
* **Input pipeline:** `image_dataset_from_directory`, 224x224 RGB, batch 32, a seeded 80/20 train/validation split of the Training folder (4,480 / 1,120 images), horizontal-flip augmentation only (`RandomFlip("horizontal")`), and `AUTOTUNE` prefetching (cell 12). There is no rotation, zoom or caching.
* **Normalization lives inside each model:** the custom CNN rescales pixels to [0, 1] (`Rescaling(1/255)`); ResNet50 applies `keras.applications.resnet50.preprocess_input` (mean subtraction, not [0, 1]). Both therefore accept raw RGB in [0, 255].
* **Model 1, custom CNN baseline** (cell 14): three Conv2D/BatchNorm/MaxPool blocks (32, 64, 128 filters), `GlobalAveragePooling2D`, `Dense(128)`, `Dropout(0.4)`, `Dense(4, softmax)`. **111,172 parameters** (110,724 trainable). Adam, lr 1e-3.
* **Model 2, ResNet50 transfer learning** (cell 16): ImageNet-pretrained ResNet50 with the backbone frozen, then `GlobalAveragePooling2D` -> `Dense(128)` -> `BatchNormalization` -> `Dropout(0.4)` -> `Dense(4, softmax)`. 23,851,012 parameters, of which 263,044 are trainable. Adam, lr 1e-4.
* **Training:** up to 15 epochs, `EarlyStopping` on validation loss (patience 4) and `ReduceLROnPlateau` for both models (cells 18, 20).
* **Evaluation (cells 24-30):** confusion matrices, per-class precision/recall/F1, one-vs-rest ROC curves, a model comparison table, a misclassification gallery, and a single-image prediction helper, all on the real `Testing` folder (1,600 images).

---

## Results (test set, 1,600 images, single run)

Source: cell 28 of the notebook (identical to `model_comparison_results.csv`).

| Metric | Custom CNN | ResNet50 (frozen backbone) |
|---|---|---|
| Test accuracy | 74.31% | 90.00% |
| Macro precision | 75.81% | 90.61% |
| Macro recall | 74.31% | 90.00% |
| Macro F1 | 70.55% | 89.75% |
| Total parameters | 111,172 | 23,851,012 |
| Trainable parameters | 110,724 | 263,044 |

### Per-class results (cell 24, 400 test images per class)

| Class | CNN precision | CNN recall | CNN F1 | ResNet50 precision | ResNet50 recall | ResNet50 F1 |
|---|---|---|---|---|---|---|
| glioma | 0.69 | 0.76 | 0.72 | 0.95 | 0.71 | 0.81 |
| meningioma | 0.80 | 0.25 | 0.38 | 0.79 | 0.91 | 0.85 |
| notumor | 0.68 | 1.00 | 0.81 | 0.92 | 1.00 | 0.96 |
| pituitary | 0.87 | 0.97 | 0.91 | 0.96 | 0.98 | 0.97 |

ResNet50 misclassified 160 of 1,600 test images (cell 30); its largest error is glioma predicted as meningioma (87 of 400 glioma scans, read from the confusion-matrix image in cell 24). The custom CNN finds only 25% of meningiomas. One-vs-rest AUC values appear only in the ROC plot legends of cell 26 (ResNet50: 0.951, 0.969, 0.999, 0.999 for glioma, meningioma, notumor, pituitary). Every number with its exact source text is in [`ml/results/existing_results.md`](ml/results/existing_results.md); the machine-readable version is [`ml/results/model_insights.json`](ml/results/model_insights.json).

---

## Known Limitations
* **Duplicates and an optimistic validation set:** cell 6 found 138 duplicate hashes (171 copies) inside Training, and the 20% validation split was drawn randomly, so copies of the same slice can sit on both sides. ResNet50 reaches 95.80% validation accuracy (cell 20) but 90.00% on the test set. The test figure is the one to trust.
* **Frozen backbone:** ResNet50 was never fine-tuned; validation loss was still falling at epoch 15.
* **Single run:** one seed, one split, no confidence intervals. Small differences should not be over-interpreted.
* **Unstable custom CNN:** its validation accuracy swung between 0.25 and 0.83 during training (cell 18), and the saved training log stops in epoch 8.
* **Not externally validated:** one public dataset only, no images from other scanners or hospitals.
* **Softmax scores are not calibrated:** a "90% confident" output is not a 90% chance of being right. No calibration analysis exists yet.
* **Weak classes:** ResNet50 glioma recall is 0.71 and meningioma precision 0.79.
* **No clinical evaluation** of any kind.

---

## Dataset Access & Download

The MRI dataset is from Kaggle, **Brain Tumor MRI Dataset** by Masoud Nickparvar:
* [https://www.kaggle.com/datasets/masoudnickparvar/brain-tumor-mri-dataset](https://www.kaggle.com/datasets/masoudnickparvar/brain-tumor-mri-dataset)

Credit goes to the dataset author and the sources he compiled. Check the dataset page for its current license and terms before reuse. The images are not included in this repository. To reproduce the training:
1. Download the dataset from the link above (or `kaggle datasets download -d masoudnickparvar/brain-tumor-mri-dataset`).
2. Extract it to a folder named `dataset/` in the project root:
   ```text
   dataset/
   ├── Training/   (glioma/ meningioma/ notumor/ pituitary/)
   └── Testing/    (glioma/ meningioma/ notumor/ pituitary/)
   ```
   The notebook's copy holds 1,400 training and 400 test images per class (5,600 and 1,600 in total).

---

## Repository Structure

```text
├── Brain_Tumor_Classification_AML.ipynb   # Main notebook: data checks, both models, evaluation (original, with saved outputs)
├── custom_cnn_model.keras                 # Saved custom CNN
├── resnet50_model.keras                   # Saved ResNet50 transfer model
├── model_comparison_results.csv           # Exported metric table (cell 28)
├── requirements.txt                       # Dependencies for the notebook
├── ml/                                    # Verified results + planned (not yet run) improvement pipeline
│   ├── results/                           #   model_insights.json, existing_results.md
│   ├── config.py, data_audit.py, train_finetune.py, evaluate.py
│   └── Brain_Tumor_Finetune_Colab.ipynb, EXPERIMENT_LOG.md, README.md
├── backend/                               # FastAPI service (inference, Grad-CAM, history, PDF report)
├── frontend/                              # React + Vite web interface
├── docs/                                  # API contract, architecture, methodology, ethics, testing, guides
└── dataset/                               # not in the repo: download it yourself
```

---

## Installation & Running the Notebook

```bash
pip install -r requirements.txt
jupyter notebook Brain_Tumor_Classification_AML.ipynb
```
Run all cells in order (Kernel > Restart & Run All). The notebook expects the dataset in `dataset/`. Dependencies: `tensorflow>=2.16.0`, `opencv-python`, `numpy`, `pandas`, `matplotlib`, `seaborn`, `scikit-learn`, `jupyter`, `ipykernel`. A GPU helps a lot (the saved custom CNN log shows about 125 s per epoch on a machine without GPU support).

---

## Web Application

The web app lets a user upload an MRI image (PNG/JPEG, max 10 MB) and see the predicted class with a probability for each class, a low-confidence warning, an optional Grad-CAM heatmap, a history of analyses stored on the local machine, a side-by-side comparison of the two models, a model-performance page fed from `ml/results/model_insights.json`, and a PDF report. Every screen carries the educational-use disclaimer.

Run it later (Python 3.10+ and Node 18+):
```bash
# backend (http://127.0.0.1:8000, API docs at /docs)
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements-backend.txt
uvicorn app.main:app --reload

# frontend (http://localhost:5173, proxies /api to the backend)
cd frontend
npm install
npm run dev
```
More detail: [`backend/README.md`](backend/README.md), [`frontend/README.md`](frontend/README.md), and in `docs/`: [API_CONTRACT](docs/API_CONTRACT.md), [ARCHITECTURE](docs/ARCHITECTURE.md), [METHODOLOGY](docs/METHODOLOGY.md), [ETHICS_AND_PRIVACY](docs/ETHICS_AND_PRIVACY.md), [TESTING](docs/TESTING.md), [DEPLOYMENT](docs/DEPLOYMENT.md), [USER_GUIDE](docs/USER_GUIDE.md), [ROADMAP](docs/ROADMAP.md), [TEAM](docs/TEAM.md), [VIVA_QA](docs/VIVA_QA.md).

---

## Planned Improvement Roadmap (planned, NOT YET RUN)

Nothing below has been executed and no result is claimed. The scripts are in [`ml/`](ml/README.md); results will be recorded in [`ml/EXPERIMENT_LOG.md`](ml/EXPERIMENT_LOG.md).
1. Duplicate and near-duplicate audit, and a duplicate-aware train/validation split.
2. Two-stage ResNet50 fine-tuning (head first, then conv5/conv4 with a low learning rate and frozen BatchNorm), mild augmentation, label smoothing, early stopping, several seeds.
3. Optionally EfficientNetV2-S.
4. Evaluation with bootstrap 95% confidence intervals, AUC, error analysis, expected calibration error and temperature scaling, and Grad-CAM galleries of correct and wrong cases.

---

## Team

| Member | Role |
|---|---|
| Soham | ML model training and evaluation (notebook, saved models) |
| Mayur | Web application (frontend and API) |
| `<Team member 3 name>` | `<role to be filled in>` |
| `<Team member 4 name>` | `<role to be filled in>` |
| `<Team member 5 name>` | `<role to be filled in>` |

(Placeholders to be completed by the team; add or remove rows as needed.)
