# Team, roles and workflow

## Members and roles

| Member | Role | Module ownership | Status |
|---|---|---|---|
| Soham | ML pipeline | `Brain_Tumor_Classification_AML.ipynb`, trained `*.keras` models, `model_comparison_results.csv`, `ml/` | confirmed |
| Mayur | Web application | `backend/` (FastAPI) and `frontend/` (React) | confirmed |
| `<Team member 3 name>` | QA, testing and documentation review | `backend/tests/`, test plans, review of `docs/` | proposed |
| `<Team member 4 name>` | Presentation, user guide and demo preparation | `presentation/`, `docs/USER_GUIDE.md`, demo rehearsal | proposed |

The last two rows are placeholders: names and roles must be filled in by the team. "Proposed" roles are suggestions only and do not describe work that has already been done.

## Authorship is shown by git history

This file states intended responsibilities, not achievements. Real authorship and the amount of work each person did are visible in the git history (`git log --author`, `git shortlog -sn`, the GitHub contributors graph). To keep that history honest:

- Each person commits their own parts under their own name and email.
- Do not commit on behalf of someone else, and do not squash other people's work into one author's commit.
- Pair work is recorded with a `Co-authored-by:` trailer naming the real co-author.
- If a section of this document is wrong, correct it in a pull request.

## Workflow

Remotes: `origin` is the personal fork, `upstream` is the shared team repository with the `dev` and `main` branches.

1. Branch from the latest `upstream/dev`: `git fetch upstream && git switch -c feature/<name>-<topic> upstream/dev`.
2. Keep branches small and focused (one feature or fix). Branch prefixes: `feature/`, `fix/`, `docs/`, `chore/`.
3. Commit using the convention in `CONTRIBUTING.md`.
4. Push to `origin` and open a pull request into **upstream `dev`**. `main` is updated from `dev` only for milestones (submission, demo).
5. Fill in the pull request template. CI (`.github/workflows/ci.yml`) must pass.
6. At least one reviewer who is not the author approves. The module owner reviews changes to their module.
7. Resolve review comments with new commits; merge when approved and green.
8. Never force-push a branch that someone else is using. Never commit large model files or datasets (see `DEPLOYMENT.md`).

## Review rules

- Authors do not merge their own pull request without a second person's approval.
- Reviewers check: correctness, tests for new behaviour, no secrets, no patient data, disclaimer and uncertain state preserved, docs updated.
- Changes to `docs/API_CONTRACT.md` need agreement from both the backend and frontend owner, because both sides code against it.
- Changes to the notebook or the saved models and the metrics CSV go through the ML owner.

## Definition of done

A change is done when:

- It meets the acceptance criteria written in the issue or pull request.
- Relevant tests are added or updated and pass locally and in CI.
- Lint passes (ruff for the backend, ESLint for the frontend once configured).
- Documentation is updated (README, API contract or the relevant `docs/` file) and `CHANGELOG.md` has an entry under "Unreleased".
- No unverified numbers are added: every metric quoted comes from the notebook outputs or the CSV.
- A second person has reviewed and approved it.

## Meetings and communication

Not recorded here. If the team agrees a cadence, add it in a pull request.
