# User guide

BrainScan AI is for education and research only. It is not a medical diagnosis (see `ETHICS_AND_PRIVACY.md`). Use only anonymous, non-patient images such as public dataset images.

Screens are described from the source code of the frontend. Wording may change slightly as the interface is polished; no screenshots are included in this file.

## Start the app

1. Start the backend: `cd backend && uvicorn app.main:app --reload` (see `CONTRIBUTING.md` for setup).
2. Start the frontend: `cd frontend && npm run dev`.
3. Open `http://localhost:5173`.

The left sidebar has five entries: Dashboard, New Analysis, History, Insights, Settings. Scan comparison (`/compare`) is reached from links inside the app. On a narrow screen the sidebar slides in from a menu button.

## Dashboard

Shows a welcome message (your name if set in Settings, otherwise "Guest"), summary cards, recent analyses, the class distribution of your predicted scans and a model performance panel. Before the first analysis it says "No analyses yet". If the performance data cannot be loaded, a static reference is shown with a note that live metrics were not available.

## New Analysis

1. Open **New Analysis**.
2. Drag an image into the drop zone or click it to choose a file. Accepted: PNG, JPG, JPEG, up to 10 MB. Other types, empty files or files that are not real images are rejected with a message.
3. Check the preview.
4. Choose the model: ResNet50 (default, the better model on the test set), Custom CNN, or both for a side-by-side comparison (if the build offers it).
5. Choose whether to generate the Grad-CAM heatmap (default on).
6. Click analyze. The first analysis after starting the server can take several seconds because the model loads then.

If you see a "model unavailable" error, TensorFlow or the `.keras` file is missing on the server.

## Results

- The predicted class and the confidence (a model score, not a probability of being right).
- A bar for each of the four classes.
- When the top score is below 0.6, the screen shows an **Uncertain result** state instead of a confident class. Treat it as "the model cannot tell".
- The original image and the Grad-CAM heatmap, to see which areas influenced the score.
- The medical disclaimer.
- Buttons to download the PDF report and to open the report view.

## Report

A printable page and a downloadable PDF with the image, heatmap (if any), class, confidence, probabilities, model version, date and disclaimer.

## History

A table of past analyses, newest first. Use the search box (id, filename, class) and the class filter; page through the list. Open a row to see its result, download its report or delete it. Delete asks for confirmation and removes the record and its files from the machine.

## Compare scans

Select two saved analyses to see them side by side (`/compare?a=<id>&b=<id>`).

## Model insights

Shows the model comparison (accuracy, macro precision, recall and F1, parameters) from the notebook's saved results, and a short explanation of how the system works and what its limits are. Real test numbers: ResNet50 90.00% accuracy, Custom CNN 74.31%.

## Settings

Profile name (shown in the top bar), analysis defaults (starting options for New Analysis), privacy information and an About section. Preferences are stored only in your browser.

## Demo mode

If the backend is not reachable, the app may offer demo data. Demo results are marked with a badge and are not produced by the model.

## Tips and troubleshooting

| Problem | What to do |
|---|---|
| Nothing loads, network errors | Check the backend is running on port 8000 and the frontend on 5173. |
| 503 on analyze | Install TensorFlow 2.16+ and make sure both `.keras` files are in the repository root. |
| 415 or 400 on upload | Use a real PNG or JPEG under 10 MB. |
| Very slow first request | The model is loading; later requests are faster. |
| Result says Uncertain | Expected for ambiguous images; do not treat it as a negative. |
