# BrainScan AI - backend (FastAPI)

REST API for brain tumor MRI classification (glioma, meningioma, notumor, pituitary) with Grad-CAM heatmaps and PDF reports. The API contract is in `../docs/API_CONTRACT.md`.

## Run (later, on a machine with Python 3.10+)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-backend.txt
uvicorn app.main:app --reload                           # http://127.0.0.1:8000  (docs at /docs)
pytest                                                  # tests use a fake model, no TensorFlow needed
```

The API starts and `/api/health` works even without TensorFlow. Models are loaded lazily on the first `/api/analyze` call (this takes a few seconds); if TensorFlow or the `.keras` file is missing the endpoint answers `503` with a clear message.

## Endpoints

| Method | Path | Notes |
|---|---|---|
| GET | `/api/health` | `{status, model_loaded, model_version, classes, models:{<id>:{available, loaded}}, tensorflow_available, demo}`; public (no API key) |
| GET | `/api/models` | `{models:[{id, name, accuracy, precision, recall, f1, parameters, trainable_parameters}]}` from `../model_comparison_results.csv`. Metrics are fractions (0.9 = 90%). |
| GET | `/api/models/insights` | verified evaluation numbers from `../ml/results/model_insights.json`; `{status:"unavailable", models:[]}` (HTTP 200) if the file is missing |
| POST | `/api/analyze?model=resnet50\|custom_cnn\|both&heatmap=true\|false` | multipart field `file` (png/jpg/jpeg, max 10 MB). Adds `low_confidence`, `confidence_threshold`, `top2`, `entropy`, `model_id`, `comparison` (non-null only for `both`) |
| GET | `/api/analyses?search=&label=&page=1&page_size=10` | newest first; `search` matches id, filename, class; `page_size` max 100 |
| GET | `/api/analyses/{id}` | one analysis |
| GET | `/api/analyses/{id}/image` | uploaded MRI |
| GET | `/api/analyses/{id}/heatmap` | Grad-CAM PNG, 404 if none |
| GET | `/api/analyses/{id}/report` | PDF report |
| DELETE | `/api/analyses?confirm=true` | purges every record and file; without `confirm=true` it answers 400. Returns `{deleted: n}` |
| DELETE | `/api/analyses/{id}` | removes the record and its files, returns `{deleted: true, id}` |
| GET | `/api/stats` | `{total_scans, last_7_days, by_class, average_confidence}` |

Errors are always `{"detail": "message"}`: 400 invalid/empty/corrupt file or bad parameter, 413 too large, 415 wrong type, 404 not found, 503 model unavailable. Validation checks the extension, the size, and that Pillow can really decode a PNG/JPEG (a renamed text file is rejected).

## Configuration

All settings are environment variables read in `app/config.py` (full list with defaults in `.env.example`). Notable ones: `CONFIDENCE_THRESHOLD` (default 0.6, below it `low_confidence` is true), `RETENTION_DAYS` (purge at startup, 0 = keep), `DATA_DIR`, `MODEL_DIR`, `API_KEY` (optional shared secret sent as `X-API-Key`), `RATE_LIMIT_PER_MIN`, `MAX_UPLOAD_MB`, `CORS_ORIGINS`, `LOG_FORMAT`. Analysis ids are `secrets.token_urlsafe(16)`. Run a single worker process (rate limiter and model cache are in memory).

## Docker

`docker build -t brainscan-backend backend` (see `Dockerfile`; the `.keras` models are mounted, not baked in; `../docker-compose.yml` wires this up). Not yet run by the author.

## Privacy

Uploaded scans, heatmaps and results are stored **only on this machine**, in `backend/data/` (`analyses.db`, `uploads/`, `heatmaps/`; git-ignored). Nothing is sent to any third party and image bytes are never logged. Delete one analysis with `DELETE /api/analyses/{id}` (or the History page), or delete everything by stopping the server and removing the `backend/data/` folder. Do not upload real patient data to a shared machine.

## Model findings (read from the `.keras` files and the notebook, without TensorFlow)

A `.keras` file is a zip; `config.json` inside was inspected.

* **Input**: both models take a raw RGB batch `(N, 224, 224, 3)` with values in **[0, 255]**. The notebook loads with `image_dataset_from_directory(image_size=(224,224), label_mode='int')` and its `predict_and_visualize_mri` helper feeds raw RGB (cv2 read, BGR->RGB, `cv2.resize` to 224x224, no scaling).
* **Normalisation lives inside the models**: Custom CNN has `Rescaling(scale=1/255)`; ResNet50 has `Lambda(keras.applications.resnet50.preprocess_input)`. So the backend must **not** divide by 255 or call `preprocess_input` (that would double-normalise). `app/preprocess.py` only converts to RGB and resizes (bilinear sampling without anti-aliasing to mimic `cv2.resize`).
* Both models also contain a `RandomFlip("horizontal")` augmentation layer, which is inactive at inference.
* **Class order**: `['glioma', 'meningioma', 'notumor', 'pituitary']` (alphabetical folder names; printed by the notebook). Output layer is a 4-unit softmax.
* **Structure**: both are flat Functional models (ResNet50 was built with `input_tensor=x`, so its layers are top-level, not nested). Saved with Keras 3 (`keras_version` 3.16 dev), so TensorFlow >= 2.16 / Keras 3 is needed.
* **Grad-CAM layers**: ResNet50 -> `conv5_block3_out` (7x7x2048); Custom CNN -> `conv2d_2` (last Conv2D, 28x28x128). `app/gradcam.py` looks the layer up by name recursively (so a ResNet50 nested inside a Sequential/Functional wrapper also works), and otherwise falls back to the last layer with a 4-D output. It uses the standard `tf.GradientTape` method: class-score gradient w.r.t. the conv map, channel-wise mean weights, weighted sum, ReLU, normalise, then a jet overlay on the 224x224 image.
* Loading uses `compile=False`; if Keras refuses the Lambda layer it retries with `safe_mode=False` (the files come from this repository).

## Layout

```
app/main.py          app factory, CORS (localhost:5173 / 127.0.0.1:5173)
app/config.py        all settings (env vars), classes, disclaimer
app/safety.py        low-confidence flag, top-2, entropy
app/security.py      optional API key, rate limit, upload-size guard
app/observability.py JSON logging + request-id middleware
app/model_service.py lazy model loading + prediction
app/preprocess.py    upload validation + preprocessing
app/gradcam.py       Grad-CAM + overlay
app/storage.py       sqlite3 + files under data/
app/report.py        reportlab PDF
app/routers/         health/models, analyses, stats
tests/               pytest + FastAPI TestClient + fake model service
```
