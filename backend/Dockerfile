# BrainScan AI backend. Build context: ./backend
# Models are NOT baked in: mount them read-only (see ../docker-compose.yml).
# config.py resolves REPO_ROOT as the parent of the code folder; with the code in /app that is "/",
# so the models are expected at /resnet50_model.keras and /custom_cnn_model.keras unless MODEL_DIR is set.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/app/data

WORKDIR /app

COPY requirements-backend.txt .
RUN pip install --no-cache-dir -r requirements-backend.txt

COPY app ./app

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"

# One worker: the rate limiter and the model cache live in process memory.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
