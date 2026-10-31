# Deployment

None of the hosted options below has been deployed or run by the team yet; they are documented routes. Do not use any hosted instance for real patient data.

## Environment variables

The backend settings live in `backend/app/config.py` (the app does not read `.env` files itself; export the variables or pass them with `--env-file` or compose). The main variables are:

| Variable | Default | Meaning |
|---|---|---|
| `CONFIDENCE_THRESHOLD` | `0.6` | Below this top probability the result is flagged `low_confidence` (Uncertain). |
| `RETENTION_DAYS` | `0` | Days to keep analyses; 0 keeps everything. Old records are purged at startup. |
| `DATA_DIR` | `backend/data` | SQLite file, uploads and heatmaps. |
| `MODEL_DIR` | repository root | Folder holding `resnet50_model.keras` and `custom_cnn_model.keras` (file names: `RESNET50_MODEL_FILE`, `CUSTOM_CNN_MODEL_FILE`). |
| `METRICS_CSV`, `INSIGHTS_JSON` | `model_comparison_results.csv`, `ml/results/model_insights.json` in the repository root | Metrics files read by `/api/models` and `/api/models/insights`. |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated allowed origins. |
| `API_KEY` | empty (open) | When set, every `/api` route except `/api/health` needs the `X-API-Key` header. A shared secret, not user login. |
| `MAX_UPLOAD_MB` | `10` | Upload size limit. |
| `RATE_LIMIT_PER_MIN` | `30` | Per client IP on `/api/analyze`; 0 turns it off. |
| `MAX_IMAGE_PIXELS` | `25000000` | Decompression-bomb guard. |
| `WARMUP` | `false` | Load models in the background at start. |
| `LOG_LEVEL`, `LOG_FORMAT` | `INFO`, `json` | Logging (`text` is also accepted). |

`backend/.env.example` lists every variable with its default; `config.py` is the authoritative source. Keep any `.env` file out of git and never commit secrets. Note that `ALLOW_UNSAFE_LAMBDA_LOAD` (default true) lets Keras run the Lambda layer stored in the model file, so only load model files you trust.

## The model file and GitHub limits

`resnet50_model.keras` is about 93.6 MB (98,186,689 bytes); `custom_cnn_model.keras` is about 1.3 MB. GitHub warns on files above 50 MB and rejects files above 100 MB in a normal push, so the ResNet50 file is close to the hard limit. Options:

1. Keep the file out of new branches and publish it as a **GitHub Release asset** (release assets allow much larger files); download it at deploy time.
2. Use Git LFS for `*.keras` (the repository would then need LFS enabled on every clone and a quota).
3. Host it on Hugging Face Hub as a model repository.

Do not retrain and re-commit variants of the model into normal git history: every version stays in the history forever.

## Option A: local (development)

```bash
# terminal 1
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements-backend.txt
uvicorn app.main:app --reload

# terminal 2
cd frontend && npm install && npm run dev
```

Open `http://localhost:5173`. Models are read from the repository root.

## Option B: docker-compose

The root `docker-compose.yml` defines `backend` and `frontend` services. It expects:

- `backend/Dockerfile` and `frontend/Dockerfile` (each folder owner adds their own; the compose file builds from `./backend` and `./frontend`).
- The `.keras` files and the metrics CSV mounted read-only from the repository root to the container location that `config.py` expects (see comments in the compose file).
- Settings are passed through the `environment:` block of the compose file (`MODEL_DIR`, `DATA_DIR`, `METRICS_CSV`, `INSIGHTS_JSON`); an optional `backend/.env` is also read if present.

```bash
docker compose up --build
# frontend on http://localhost:8080, backend on http://localhost:8000
```

The compose file was written without being run; expect to adjust it. `config.py` lets the model and data folders be set with `MODEL_DIR` and `DATA_DIR`, and the compose file uses that to mount the models read-only at `/models` and keep history in a named volume at `/data`, independent of where the Dockerfile copies the code.

## Option C: Hugging Face Space for the API

1. Create a Docker Space.
2. Add a Dockerfile that installs `requirements-backend.txt` and starts `uvicorn app.main:app --host 0.0.0.0 --port 7860`.
3. In the container start-up, download `resnet50_model.keras` from the hosted release (for example with `curl -L` or `huggingface_hub`) into the expected path instead of committing it.
4. Set `CORS_ORIGINS` to the static frontend origin (the default allows only localhost).
5. Remember the free tier may sleep and may have an ephemeral disk, so history can vanish.

## Option D: static hosting for the frontend

`npm run build` creates `frontend/dist/`, which any static host can serve (GitHub Pages, Netlify, Cloudflare Pages). The code calls relative `/api/...`, so in production either put a reverse proxy in front that routes `/api` to the backend, or add a configurable API base URL to `frontend/src/lib/api.js` (not present today). Configure the host to serve `index.html` for unknown paths so client-side routes work.

## Production cautions

- Only an optional shared `API_KEY` exists (no user accounts); do not expose it with real data.
- Use HTTPS in any hosted setup.
- TensorFlow makes the backend image large (several hundred MB to a few GB).
- SQLite is single-writer; run one backend process.
