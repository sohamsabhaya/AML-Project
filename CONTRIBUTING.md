# Contributing

Thanks for working on BrainScan AI. Read `docs/TEAM.md` for roles and workflow, and `docs/API_CONTRACT.md` before changing anything that crosses the frontend/backend boundary.

## Setup

Prerequisites: Git, Python 3.10 or newer, Node.js 20.

```bash
git clone git@github.com:sohamsabhaya/AML-Project.git     # or your fork
cd AML-Project
```

Backend (no TensorFlow needed to run the tests):

```bash
cd backend
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements-backend.txt
uvicorn app.main:app --reload        # http://127.0.0.1:8000, docs at /docs
pytest
```

`requirements-backend.txt` currently includes TensorFlow because the API runs the models. CI uses a dev requirements file without TensorFlow (see `.github/workflows/ci.yml`); if `backend/requirements-dev.txt` is not present yet, create it with `fastapi`, `python-multipart`, `pillow`, `numpy`, `reportlab`, `httpx`, `pytest` and `ruff`.

Frontend:

```bash
cd frontend
npm install
npm run dev                          # http://localhost:5173, proxies /api to :8000
npm run build
```

The `.keras` model files are expected in the repository root (`resnet50_model.keras`, `custom_cnn_model.keras`). Do not commit new or retrained model files without agreeing it with the ML owner (they are large).

## Branches and pull requests

- Branch from `upstream/dev`; name it `feature/<name>-<topic>`, `fix/...`, `docs/...` or `chore/...`.
- Open pull requests into upstream `dev`.
- Keep pull requests small; one concern per pull request.

## Commit message convention

Conventional Commits style:

```
<type>(<scope>): <short imperative summary, max ~72 chars>

<optional body: what and why, not how>
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`, `style`, `perf`.
Scopes: `backend`, `frontend`, `ml`, `docs`, `ci`, `presentation`.

Examples: `feat(backend): add entropy to analysis response`, `docs: describe retention settings`.

## Pull request checklist

- [ ] Branch is up to date with `upstream/dev`.
- [ ] Tests added or updated; `pytest` and `npm test` pass (where configured).
- [ ] Lint passes (`ruff check backend`, `npm run lint`).
- [ ] `npm run build` succeeds for frontend changes.
- [ ] `docs/API_CONTRACT.md` updated if an endpoint or field changed, with agreement from both owners.
- [ ] The medical disclaimer text and the uncertain state are unchanged or deliberately updated.
- [ ] No secrets, `.env` files, patient data, datasets or model files added.
- [ ] Any number quoted in docs or UI comes from the notebook outputs or `model_comparison_results.csv`.
- [ ] `CHANGELOG.md` has an entry under "Unreleased".
- [ ] A second person has been requested as reviewer.

## Style

- Python: ruff for linting; type hints for public functions; keep `app/config.py` as the only place for constants.
- JavaScript: functional React components, API calls only through `frontend/src/lib/api.js`.
- Write comments and docs in plain English; do not add claims that are not backed by the repository.

## Reporting issues

Use the issue templates under `.github/ISSUE_TEMPLATE/`. Do not attach real patient images.
