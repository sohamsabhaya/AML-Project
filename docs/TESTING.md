# Testing

## What exists today

Backend: `backend/tests/` with pytest, FastAPI `TestClient` and a fake model service (no TensorFlow needed). `test_api.py` currently covers the following (the file is still growing; run `pytest --collect-only -q` for the exact list):

- health; models read from the CSV
- analyze a PNG; preprocessing passes raw 0-255 values; analyze without heatmap and with the custom model
- heatmap failure does not fail the analysis
- unknown model gives 400; invalid extension 415; a fake image with a PNG extension 400; empty file 400; GIF renamed to PNG 415; oversize 413; missing file field 400; model unavailable 503
- list with pagination, search and filter; get and delete; delete removes files; bad ids give 404
- report is a PDF, with and without heatmap; stats; CORS allows the Vite origin; filename sanitising
- v1.1 behaviour: confidence flag, threshold from config, entropy bounds, `model=both` (agree and disagree), unguessable ids, safety fields in list items, purge requires `confirm=true`, insights file present and missing, retention purge at startup, legacy rows upgraded

Frontend: `frontend/package.json` lists Vitest, Testing Library, jsdom and ESLint as dev dependencies, but it defines no `test` or `lint` script, and no test file or ESLint config was found in `frontend/`. So no frontend test runs today. The CI workflow calls `npm run lint` and `npm test` with `--if-present`, so it passes and will start running them once those scripts exist.

CI note: the backend CI job installs `backend/requirements-dev.txt`, which was not in the repository when this was checked; create it (without TensorFlow) or that job will fail.

Notebook: the saved outputs include a data integrity audit (cell 6) and the final test evaluation (cells 28 and 30). There are no automated ML tests.

## How to run

```bash
cd backend
pip install -r requirements-backend.txt      # or requirements-dev.txt (once it exists) for the light set
pytest
ruff check .

cd ../frontend
npm ci
npm run build
```

The same steps run in GitHub Actions (`.github/workflows/ci.yml`).

## What is not covered

- No test loads the real `.keras` models; accuracy of the real model through the API is not tested.
- Grad-CAM is tested only through the fake service (a failure path), not numerically.
- No frontend unit, component or end-to-end tests.
- The API key check, the rate limiter (429) and the early upload guard have no dedicated tests in the list above.
- No accessibility audit, no cross-browser testing, no load testing.
- The upload limit and file validation are tested; adversarial files (for example crafted images beyond the pixel limit) are not exhaustively tested.
- Docker and hosted deployment are untested.
- Model quality tests on external data do not exist (see `METHODOLOGY.md`).

## Manual pre-demo checklist

- [ ] Backend starts; `/api/health` returns ok; `/docs` opens.
- [ ] Upload a public dataset image for each class; results appear.
- [ ] A non-image file renamed to `.png` is rejected.
- [ ] Heatmap appears; PDF downloads and opens.
- [ ] An ambiguous image shows the Uncertain state (or lower the threshold temporarily to check the UI).
- [ ] Disclaimer text is visible on results and in the PDF.
- [ ] History search, filter, delete with confirmation work.
- [ ] Demo mode badge shows when the backend is off.
- [ ] Test on a narrow window (phone width).

## Planned

Component tests with Vitest and Testing Library, a Playwright smoke test, one integration test using the real model in a separate (non-CI) job.
