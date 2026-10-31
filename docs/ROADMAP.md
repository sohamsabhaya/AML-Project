# Roadmap

Everything here is **planned**. None of it is implemented unless the changelog says so. Priorities: P1 before any further demo, P2 next, P3 later.

## P1 - Validity and safety

| Item | Why | Area |
|---|---|---|
| De-duplicate Training (exact plus perceptual hashes), re-split, retrain | 138 duplicate hashes (171 copies) make validation optimistic | ML |
| Per-class metrics and confusion matrices: done in `ml/results/model_insights.json`. Still needed: confidence intervals and calibration (script written in `ml/evaluate.py`, not run) | Quality evidence | ML |
| Check the shipped UI against `ETHICS_AND_PRIVACY.md` section 7 (uncertain state, disclaimer, wording) | Safety requirements must hold in the build | Web, QA |
| Frontend tests and lint in CI | No frontend tests today | Web |
| Make the frontend API base URL configurable (CORS origins are already configurable through `CORS_ORIGINS`) | Needed for any hosted deployment | Web |

## P2 - Model quality

- Fine-tune the top ResNet50 blocks and compare with the frozen baseline.
- Repeat training with several seeds; report mean and spread.
- Temperature scaling and reliability diagrams; revisit the 0.6 threshold with calibrated scores.
- Out-of-distribution detection so that non-MRI images are rejected rather than labelled.
- External validation on a dataset from another source, if one is available.

## P2 - Web application

- Dockerfiles for backend and frontend (being added) and a verified `docker-compose.yml` (written, not run).
- Run the fine-tuning pipeline in `ml/` (written, never executed) and report real results.
- Real-model integration test in a separate CI job.
- Accessibility audit (keyboard, contrast, screen reader labels).
- Deploy the API (Hugging Face Space) and the static frontend as a public demo, with synthetic or public images only.

## P3 - Nice to have

- Authentication and per-user history if multi-user use is ever required (also requires a privacy review).
- Batch upload.
- Export of history as CSV.
- Model versioning shown in the UI and a model registry folder.
- DICOM support (would need de-identification handling first).

## Not planned

Clinical use, integration with hospital systems, and any claim of diagnostic performance.
