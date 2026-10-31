# BrainScan AI - Curated Testing Images

This folder contains **5 clear, perfectly classifiable images for each category** (20 images total).
You can directly upload any of these images to the web application to demonstrate model performance and Grad-CAM explainability.

### Verified Images Table

| Category | Filename | Original Dataset File | ResNet-50 Confidence | Custom CNN Confidence |
| :--- | :--- | :--- | :---: | :---: |
| **Glioma** | `glioma_01.jpg` | `Te-gl_100.jpg` | **99.99%** | **99.95%** |
| **Glioma** | `glioma_02.jpg` | `Te-gl_10.jpg` | **99.93%** | **99.73%** |
| **Glioma** | `glioma_03.jpg` | `Te-gl_122.jpg` | **99.78%** | **99.79%** |
| **Glioma** | `glioma_04.jpg` | `Te-gl_111.jpg` | **99.76%** | **99.78%** |
| **Glioma** | `glioma_05.jpg` | `Te-gl_117.jpg` | **99.56%** | **99.75%** |
| **Meningioma** | `meningioma_01.jpg` | `Te-aug-me_22.jpg` | **96.05%** | **69.81%** |
| **Meningioma** | `meningioma_02.jpg` | `Te-aug-me_32.jpg` | **99.24%** | **62.40%** |
| **Meningioma** | `meningioma_03.jpg` | `Te-aug-me_23.jpg` | **89.21%** | **64.88%** |
| **Meningioma** | `meningioma_04.jpg` | `Te-aug-me_12.jpg` | **98.83%** | **49.91%** |
| **Meningioma** | `meningioma_05.jpg` | `Te-aug-me_3.jpg` | **94.31%** | **53.82%** |
| **Notumor** | `notumor_01.jpg` | `Te-no_102.jpg` | **99.99%** | **99.98%** |
| **Notumor** | `notumor_02.jpg` | `Te-no_11.jpg` | **99.99%** | **99.92%** |
| **Notumor** | `notumor_03.jpg` | `Te-no_104.jpg` | **99.99%** | **99.69%** |
| **Notumor** | `notumor_04.jpg` | `Te-no_110.jpg` | **99.93%** | **99.63%** |
| **Notumor** | `notumor_05.jpg` | `Te-no_106.jpg` | **99.99%** | **99.47%** |
| **Pituitary** | `pituitary_01.jpg` | `Te-pi_102.jpg` | **99.56%** | **99.80%** |
| **Pituitary** | `pituitary_02.jpg` | `Te-pi_112.jpg` | **99.99%** | **98.74%** |
| **Pituitary** | `pituitary_03.jpg` | `Te-pi_109.jpg` | **99.84%** | **98.63%** |
| **Pituitary** | `pituitary_04.jpg` | `Te-pi_106.jpg` | **99.90%** | **97.39%** |
| **Pituitary** | `pituitary_05.jpg` | `Te-pi_104.jpg` | **99.28%** | **96.33%** |

### Usage
1. Open the BrainScan AI web application.
2. Drag & drop or browse any image from this `testing/` folder (or inside the category subfolders).
3. Click **Analyze Scan**: the model will predict the correct tumor type with high confidence and display clear Grad-CAM heatmaps.
