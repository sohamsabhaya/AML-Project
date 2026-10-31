# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/) once a release is tagged. Entries describe only what exists in the repository; see `git log` for the full history.

## [Unreleased]

### Added
- Documentation set under `docs/`: architecture, methodology, ethics and privacy, team workflow, user guide, deployment, testing, viva questions and roadmap.
- `CONTRIBUTING.md`, GitHub pull request and issue templates, a CI workflow (frontend lint, test and build; backend ruff and pytest) and `.gitattributes`.
- Root `docker-compose.yml` for running backend and frontend together (written but not yet run by the team).
- Group presentation deck and speaker material under `presentation/`.
- Backend hardening: optional API key, per-IP rate limit, early upload guard, structured logging with request ids, retention purge, purge-all with confirmation, `model=both`, low-confidence flag, entropy and top-2 fields, `/api/models/insights`.
- `ml/` folder: written but unexecuted improvement pipeline, plus verified per-class results in `ml/results/model_insights.json`.

### Changed
- API contract extended to v1.1 (low-confidence flag, entropy, top-2 classes, comparison mode, insights endpoint, retention setting, `/insights` and `/compare` routes).

## [0.1.0] - Initial web application

### Added
- Notebook `Brain_Tumor_Classification_AML.ipynb` with a custom CNN baseline and a ResNet50 transfer-learning model, saved as `custom_cnn_model.keras` and `resnet50_model.keras`, with the comparison table in `model_comparison_results.csv` (test accuracy 74.31% and 90.00%).
- FastAPI backend (`backend/`): health, model metrics, analysis upload with Grad-CAM heatmap, history list, detail, image, heatmap and PDF report endpoints, delete, stats; SQLite and file storage under `backend/data/`; upload validation (type, size, real image decode); pytest suite with a fake model service.
- React and Vite frontend (`frontend/`): dashboard, new analysis, results, history, report and settings pages with a shared UI component set and a demo mode.
- API contract (`docs/API_CONTRACT.md`).
