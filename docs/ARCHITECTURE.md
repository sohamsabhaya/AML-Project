# BrainScan AI - Architecture

BrainScan AI is an educational web application that classifies a brain MRI slice into one of four classes (glioma, meningioma, notumor, pituitary), shows a Grad-CAM heatmap, and keeps a local history with PDF reports. The ML models come from the notebook `Brain_Tumor_Classification_AML.ipynb`; the web application (React frontend and FastAPI backend) wraps them. The HTTP interface is specified in `API_CONTRACT.md`; this document explains how the parts fit together.

## 1. System context

```mermaid
flowchart LR
    U[User: student, teacher or reviewer] -->|browser| FE[BrainScan AI frontend]
    FE -->|HTTP /api| BE[BrainScan AI backend]
    BE -->|loads| M[(resnet50_model.keras<br/>custom_cnn_model.keras)]
    BE -->|reads| CSV[(model_comparison_results.csv<br/>ml/results/model_insights.json)]
    BE -->|writes| D[(Local data folder:<br/>SQLite + uploads + heatmaps)]
    DS[(Kaggle brain tumor MRI dataset)] -.->|used offline for training only| NB[Training notebook]
    NB -.->|produces| M
    NB -.->|produces| CSV
```

The dataset is never part of the running system. Nothing is sent to third-party services: uploads stay on the machine that runs the backend.

## 2. Components

```mermaid
flowchart TB
    subgraph Frontend [frontend/ - React + Vite]
        Pages[pages: Dashboard, NewAnalysis, Results, History, Report, Insights, Compare, Settings]
        Comp[components: ui and analysis]
        Lib[lib: api.js, classes.js, format.js, mock.js]
        Pages --> Comp
        Pages --> Lib
    end
    subgraph Backend [backend/app - FastAPI]
        Mid[middleware: request id, CORS, analyze guard]
        Sec[safety.py and security.py: uncertainty, API key, rate limit]
        Routers[routers: health/models/insights, analyses, stats]
        Pre[preprocess.py: validate + resize]
        MS[model_service.py: lazy load + predict]
        GC[gradcam.py]
        ST[storage.py: sqlite3 + files]
        RP[report.py: PDF]
        CFG[config.py]
        Mid --> Routers
        Routers --> Sec
        Routers --> Pre
        Routers --> MS
        Routers --> GC
        Routers --> ST
        Routers --> RP
        MS --> CFG
    end
    Lib -->|fetch /api/...| Routers
    MS --> K[(.keras files)]
    ST --> FS[(backend/data)]
```

Design points:

- The frontend only talks to `/api/...` with relative URLs. In development the Vite dev server proxies `/api` to `http://127.0.0.1:8000`.
- The API starts and `/api/health` answers even without TensorFlow. Models load lazily on the first analysis, so a missing model gives a clear `503` instead of a crash at startup.
- `lib/mock.js` provides a demo mode so the UI can be shown without a backend; demo results are marked with a badge.
- The saved models embed their own preprocessing (`Rescaling(1/255)` in the custom CNN, ResNet50 `preprocess_input` in a Lambda layer). The backend therefore only converts to RGB and resizes to 224x224 and feeds raw 0-255 values.

## 3. Analyze-request sequence

```mermaid
sequenceDiagram
    actor User
    participant UI as Frontend (NewAnalysis)
    participant API as FastAPI router
    participant PRE as preprocess
    participant MS as model_service
    participant GC as gradcam
    participant DB as storage

    User->>UI: choose image, model, heatmap option
    UI->>API: POST /api/analyze?model=resnet50&heatmap=true (multipart file)
    API->>PRE: validate extension, size, decode with Pillow
    PRE-->>API: 224x224 RGB array (0-255)
    API->>MS: predict(array, model)
    Note over MS: first call loads the .keras file (a few seconds)
    MS-->>API: 4 softmax probabilities
    API->>GC: heatmap(model, array, class)
    GC-->>API: overlay PNG (a failure here does not fail the analysis)
    API->>DB: save upload, heatmap, row
    DB-->>API: id
    API-->>UI: Analysis JSON (class, confidence, probabilities, low_confidence)
    UI->>User: Results page (uncertain state if confidence < 0.6)
```

Before the router runs, `AnalyzeGuardMiddleware` can reject a request early (`413` oversize, `429` rate limit per client IP); `401` is returned for a bad key when `API_KEY` is set. `model=both` runs both models and adds a `comparison` object. Error paths: `400` unreadable, empty or corrupt file or bad parameter; `401`; `413` too large (more than 10 MB by default, `MAX_UPLOAD_MB`); `415` wrong type; `429` too many requests; `503` model unavailable. All errors have the shape `{"detail": "..."}`.

## 4. Data model of stored analyses

Implemented in `backend/app/storage.py` (SQLite table `analyses`, plus files on disk). Schema version 2 adds the columns `low_confidence`, `confidence_threshold`, `top2`, `entropy`, `model_id` and `comparison`; older rows are upgraded when the database is opened (`test_legacy_rows_are_upgraded`). The diagram below shows the original core columns.

```mermaid
erDiagram
    ANALYSES {
        TEXT id PK "secrets.token_urlsafe(16), unguessable"
        TEXT created_at "ISO 8601 UTC"
        TEXT filename "sanitised original name"
        TEXT predicted_class "glioma|meningioma|notumor|pituitary"
        REAL confidence "max probability, 0-1"
        TEXT probabilities "JSON, 4 values"
        TEXT model_version "e.g. resnet50-v1"
        TEXT image_file "path under data/uploads"
        TEXT heatmap_file "nullable, path under data/heatmaps"
    }
    UPLOAD_FILE ||--|| ANALYSES : "image_file"
    HEATMAP_FILE |o--|| ANALYSES : "heatmap_file"
```

Deleting an analysis removes the row and both files. An index on `created_at DESC` serves the history list. `DELETE /api/analyses?confirm=true` purges everything, and `RETENTION_DAYS` (default 0, keep) purges old records at startup.

## 5. Deployment view

```mermaid
flowchart LR
    subgraph Dev [Local development]
        B1[Browser :5173] --> V[Vite dev server] -->|proxy /api| A1[uvicorn :8000]
        A1 --> F1[(repo root models + backend/data)]
    end
    subgraph Opt [Optional hosted setup - planned/optional]
        B2[Browser] --> S[Static host: frontend build]
        S -->|HTTPS /api| H[Hugging Face Space: API container]
        H --> R[(model downloaded from a hosted release at start)]
    end
```

Details, commands and trade-offs are in `DEPLOYMENT.md`. The hosted option has not been deployed by the team; it is a documented route, not a running service.

## 6. Module ownership map

| Area | Path | Owner (see TEAM.md) |
|---|---|---|
| Notebook, training, saved models, metrics CSV | `Brain_Tumor_Classification_AML.ipynb`, `*.keras`, `model_comparison_results.csv`, `ml/` | Soham |
| Backend API | `backend/` | Mayur |
| Frontend | `frontend/` | Mayur |
| Documentation, CI, delivery | `docs/`, `.github/`, `presentation/` | shared; see TEAM.md |

Git history is the source of truth for who changed what.

## 7. Technology choices and reasons

| Choice | Reason |
|---|---|
| TensorFlow/Keras | The notebook and saved `.keras` files already use it; Keras 3 (TensorFlow 2.16 or newer) is needed to load them. |
| ResNet50 transfer learning | Pretrained features help with a small dataset (5,600 training images); see METHODOLOGY.md. |
| FastAPI | Typed request handling, automatic `/docs` page, simple multipart upload, easy to test with `TestClient`. |
| SQLite (`sqlite3`) + files | Zero-setup, single-user, local storage that matches the privacy stance (nothing leaves the machine). Not meant for concurrent multi-user use. |
| Pillow | Verifies that an upload really decodes as PNG or JPEG, so a renamed text file is rejected. |
| reportlab | Pure-Python PDF generation, no system dependencies. |
| React + Vite | Fast dev loop, simple static build that any static host can serve. |
| react-router-dom | Client-side routes such as `/results/:id` and `/compare`. |
| Recharts | Charts for dashboard and model comparison. |
| lucide-react | Icon set. |
| pytest + FastAPI TestClient with a fake model service | Backend tests run without TensorFlow, so CI stays light. |

## 8. Known architectural limits

- Single-user: there are no accounts and no multi-tenant isolation. An optional shared `API_KEY` (header `X-API-Key`) and a per-IP rate limit exist, but anyone with the key can read every stored analysis. Do not expose the API publicly with real patient data.
- Run a single backend worker: the rate limiter and the model cache are in memory.
- Analyses are stored in one SQLite file on the host; hosted free tiers may have ephemeral disks.
- The 93.6 MB ResNet50 file is above GitHub's 50 MB soft warning and below its 100 MB hard block, so it needs care (see `DEPLOYMENT.md`).
