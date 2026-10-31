# Ethics and Privacy

## 1. Status of the software

BrainScan AI is a university course prototype. It is **not a medical device**, has not been clinically validated, has no regulatory clearance, and must not be used to diagnose, screen, triage or rule out any condition. The text shown in the app is:

> AI-generated prediction for educational and research use only. It is not a medical diagnosis and must not replace review by a qualified clinician.

## 2. Intended use

- Demonstrating a machine learning pipeline and a web interface to students and teachers.
- Showing how a classifier, an explanation heatmap and an uncertainty state fit together.
- Comparing a small CNN with a transfer-learning model on public data.

Out of scope: any use on real patients, any clinical workflow, any decision about treatment, insurance or employment.

## 3. Data handling

- Training data is the public Kaggle brain tumor MRI dataset (Nickparvar, 2021), built on the figshare collection by Cheng et al. (2015). It is not stored in the repository.
- Uploaded scans, heatmaps and results are stored only on the machine running the backend, in `backend/data/` (SQLite file, `uploads/`, `heatmaps/`). The folder is git-ignored.
- Nothing is sent to a third party. Image bytes are not written to logs.
- Record ids are unguessable random strings. Filenames are sanitised before storage.
- Uploads are validated: extension, size (at most 10 MB by default), a real PNG or JPEG decode and a pixel limit. Access logs do not record image bytes, file names or record ids.
- There are no user accounts. An optional shared `API_KEY` and a per-IP rate limit can be switched on for a demo deployment; they are not user authentication.

## 4. Retention and deletion

- Each analysis can be deleted from the History page (`DELETE /api/analyses/{id}`), which removes the row and the stored files.
- A purge-all call (`DELETE /api/analyses?confirm=true`) and an optional `RETENTION_DAYS` setting (0 keeps everything, purge at startup) are implemented in the backend and covered by tests.
- To remove everything, stop the server and delete `backend/data/`.
- On a hosted free tier, disks may be ephemeral, so data may disappear without a deliberate delete; that is not a retention guarantee.

## 5. No protected health information

Do not upload images that contain patient names, identifiers, dates of birth or burned-in annotations, and do not upload real patient scans to a shared or hosted instance. The app does not collect names, ages or other patient metadata, and has no accounts. It does store the original filename, so filenames must not contain personal data; use anonymous names.

## 6. Risks

| Risk | Why it matters here |
|---|---|
| Automation bias | A confident-looking percentage invites trust. The softmax score is uncalibrated and may be high on a wrong answer. |
| Overstated accuracy | 90.00% on a balanced test set from one source does not transfer to new scanners or populations; patient-level independence is unknown. |
| Out-of-distribution input | Any image (a non-brain image, a different sequence, a 3-D slice orientation not in the data) still receives one of four labels. |
| False reassurance | A "no tumor" output could be read as "healthy". |
| Misleading explanation | Grad-CAM heatmaps are coarse and can look plausible when the prediction is wrong. |
| Privacy leakage | Uploaded files with identifying metadata or filenames. |
| Misuse | Using the tool outside its stated purpose. |

## 7. How the UI mitigates these risks

This section states the design requirements from API contract v1.1 and the UI plan. The frontend was still being changed while this document was written, so before the demo each item should be checked against the running app (the "Testing" section of `TESTING.md` lists this as a manual check). If an item is missing in the build, treat it as a defect, not as a claim that holds.

- Uncertain state: when the highest probability is below 0.6 (`CONFIDENCE_THRESHOLD`), the result page shows "Uncertain result" instead of a confident class.
- The exact disclaimer above appears on result screens and in the PDF report.
- Wording avoids reassurance: the "No Tumor" outcome is described as the model's prediction on this image, not as a statement that the person is healthy, and the interface never says "normal", "safe" or "all clear".
- Probabilities for all four classes and the runner-up class are shown, so the user sees the alternatives, not only the top label.
- Heatmap is optional and labelled as an explanation aid.
- A model comparison page shows the real test results, including the lower-performing baseline, and the Insights page states the limitations.
- Demo mode is visibly badged so mock results cannot be mistaken for model output.
- Deletion is one click, with a confirmation dialog.

These mitigations reduce but do not remove the risks. The main control is the intended-use rule: educational use only.

## 8. Fairness and representativeness

The dataset documentation available to the team does not describe patient demographics, scanners or sites. Subgroup performance (age, sex, scanner) is therefore unknown and has not been measured. No claim of fairness across populations is made.

## 9. Responsibilities

The team is responsible for keeping the disclaimer and the uncertain state intact in any UI change. Any future move toward real data would require ethics review, consent, data-protection compliance and clinical validation, none of which are part of this project.
