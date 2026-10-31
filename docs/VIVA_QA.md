# Viva questions and honest answers

Numbers: test set 1,600 images (400 per class). ResNet50: 90.00% accuracy, macro P/R/F1 90.61/90.00/89.75, 23,851,012 parameters of which 263,044 trainable. Custom CNN: 74.31%, 75.81/74.31/70.55, 111,172 parameters (110,724 trainable). Anything not in the notebook outputs is said to be unknown.

## A. Machine learning (Soham's area)

**1. What problem does the project solve?**
Four-class classification of a brain MRI slice: glioma, meningioma, pituitary, no tumor. It is an educational prototype, not a diagnostic system.

**2. Which dataset did you use and how big is it?**
The Kaggle Brain Tumor MRI Dataset (Nickparvar, 2021), built on the figshare collection of Cheng et al. The notebook uses 5,600 training and 1,600 testing images, exactly 25% per class.

**3. Why is the test accuracy of ResNet50 higher than the custom CNN?**
ResNet50 starts with ImageNet features learned from millions of images, while the custom CNN learns everything from 4,480 training images. The test results are 90.00% against 74.31%. We did not run an ablation, so the explanation is plausible but not proven.

**4. Why is the backbone frozen?**
To keep training cheap and reduce overfitting on a small dataset; only 263,044 of 23.85 million parameters are trained. Fine-tuning is planned, not done, and might improve results.

**5. Is 90% good?**
For a frozen-backbone baseline on a balanced, single-source dataset it is reasonable, but it is not clinically adequate and the figure has no confidence interval. With 1,600 images the sampling error is around a point or two (our rough estimate).

**6. What is data leakage and did you have any?**
Leakage means test information influences training. The notebook found 0 identical images between Training and Testing by exact hashing. It found 138 duplicated hashes (171 extra copies) inside Training, so the validation split is optimistic. Near-duplicates and patient overlap could not be checked.

**7. Why is validation accuracy (95.80%) higher than test accuracy (90.00%)?**
Probably in part because of duplicates and similar slices crossing the training/validation split, and possibly patient overlap. This is a hypothesis; we did not isolate the cause.

**8. What is macro F1 and why report it?**
The unweighted mean of per-class F1. Because classes are balanced it is close to accuracy, but it still penalises a weak class. ResNet50 macro F1 is 89.75%, custom CNN 70.55%.

**9. Why is the custom CNN's F1 (70.55%) lower than its accuracy (74.31%)?**
Because some classes are predicted poorly. Its meningioma recall is only 0.25 (129 of 400 meningiomas were called glioma and 125 notumor), while notumor recall is 1.00 but precision 0.68. Per-class numbers are in `ml/results/model_insights.json`.

**10. How is preprocessing done?**
Raw RGB at 224 x 224 enters the model; each model contains its own scaling layer (rescaling by 1/255, or ResNet50 `preprocess_input`). The web backend only converts to RGB and resizes, so inference matches training.

**11. What is Grad-CAM and can we trust it?**
It highlights regions whose feature maps most increase the predicted class score. It is an aid, not proof; for ResNet50 it is a coarse 7 x 7 grid and has not been validated against expert annotations.

**12. What does the confidence number mean?**
It is the maximum softmax output and is uncalibrated: 0.9 does not mean 90% chance of being right. The notebook states this too.

**13. What would you do next on the ML side?**
De-duplicate and re-split, repeat runs with several seeds, fine-tune, calibrate with temperature scaling, and test on an external dataset. All are planned, none are done.

**14. Why not use a bigger or newer model?**
ResNet50 is a well-understood baseline (He et al., CVPR 2016) that is easy to explain and reproduce. We did not compare other backbones, so we make no claim it is the best choice.

**15. How did you avoid overfitting?**
Augmentation, dropout 0.4, batch normalization, early stopping on validation loss and learning-rate reduction. The custom CNN's early validation curve was very unstable, so we cannot claim it was well behaved.

## B. Web application (Mayur's area)

**16. Describe the architecture.**
React and Vite frontend calling a FastAPI backend under `/api`. The backend validates uploads, runs the Keras model, creates a Grad-CAM overlay, stores results in SQLite and files, and builds PDF reports. See `ARCHITECTURE.md`.

**17. Why FastAPI and SQLite?**
FastAPI gives typed endpoints and automatic documentation and is easy to test. SQLite needs no setup and fits a single-user local tool. It is not suitable for many concurrent users.

**18. How do you validate an upload?**
Extension, size limit (10 MB), and a real decode with Pillow, with a pixel limit against decompression bombs. A text file renamed to `.png` gets a 400; a GIF renamed to PNG gets 415. These cases are tested.

**19. Why load the model lazily?**
So the API starts quickly and `/api/health` works even without TensorFlow; a missing model returns a clear 503. The cost is a slow first analysis.

**20. How do you test without TensorFlow?**
Tests inject a fake model service into `create_app`. That means the real model's output through the API is not covered by automated tests.

**21. What does the uncertain state do?**
If the top probability is below 0.6 (configurable), the UI shows "Uncertain result" instead of a confident label. 0.6 is a pragmatic threshold, not calibrated.

**22. How is the frontend kept in sync with the backend?**
Through `docs/API_CONTRACT.md`; the frontend calls only through `lib/api.js` and has a demo mode with mock data for work without the backend.

**23. What happens to a user's uploaded image?**
It is stored only on the host in `backend/data/`, never sent elsewhere, and can be deleted from History. There are no accounts or authentication.

**24. What are the security weaknesses?**
No user accounts; only an optional shared API key and an in-memory per-IP rate limit, single-user storage, CORS limited to localhost by default, and the model loader may execute a Lambda layer from the model file, so only trusted model files may be used. It must not be exposed publicly with real data.

**25. Can it be deployed online?**
Documented routes exist (Docker Compose, a Hugging Face Space, static frontend hosting) but we have not deployed it. The 93.6 MB model sits near GitHub's 100 MB limit, so it should be fetched from a release.

**26. What frontend tests exist?**
None run today: Vitest and Testing Library are listed as dev dependencies, but no test script or test file exists yet; CI only builds. This is a known gap (see `TESTING.md`).

## C. Ethics and safety

**27. Could this be used clinically?**
No. It is not a medical device, is not clinically validated and was trained on one public dataset. The disclaimer is on every result and report.

**28. What is automation bias and how do you reduce it?**
People over-trust machine outputs. We show all four probabilities, an uncertain state, a heatmap labelled as an explanation aid, the disclaimer, and avoid reassurance wording for "No Tumor". This reduces but does not remove the risk.

**29. What if someone uploads a non-brain image?**
The model still returns one of four labels, because it was not trained to reject out-of-distribution inputs. This is a limitation; an out-of-distribution check is a roadmap item.

**30. Are the results fair across patient groups?**
Unknown. The dataset documentation we have does not provide demographics or scanner details, so we cannot measure subgroup performance.

**31. Why is class balance a problem for real use?**
The test set is 25% per class. Real prevalence differs, so the real-world precision of a "tumor" prediction would not match the reported precision.

**32. What data does the app keep, and for how long?**
Image, heatmap, class, probabilities, filename and time, until deleted; an optional retention setting (`RETENTION_DAYS`, off by default) deletes old records at startup. No patient metadata is collected.

## D. Teamwork and process

**33. How did the team split the work?**
Soham owned the ML pipeline and models; Mayur the web application. Other members' roles are listed as proposed in `TEAM.md` and need to be confirmed. Real contributions are visible in git history.

**34. What was the Git workflow?**
Feature branches from upstream `dev`, pull requests into `dev`, a second reviewer, and CI that must pass. See `TEAM.md`.

**35. How do you know the numbers in the slides are correct?**
They come from `model_comparison_results.csv` and the saved notebook outputs; anything that could not be read there was left out.

**36. What would you do differently?**
Start with a patient-aware split and de-duplication, agree the API contract and tests earlier, and add frontend tests from the start.

**37. What is the most important integration pitfall?**
Matching the web preprocessing to the notebook: the models embed their own scaling, so adding another divide-by-255 or `preprocess_input` in the backend would silently degrade predictions. The backend therefore feeds raw 0-255 values, and a test checks this.
