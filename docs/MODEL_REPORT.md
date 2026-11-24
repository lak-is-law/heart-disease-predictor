# CardioSense model: what was tried and what it shows

Internal validation only: 303 patients from the Cleveland Clinic, repeated stratified 5-fold cross-validation
(6 repeats here, 20 in `evaluate.py`). Reproduce with `python benchmark.py`.

## Result: no model family beats the shipped logistic regression

| Model | AUC, all 13 inputs | AUC, first-visit inputs (7) |
|---|---|---|
| Logistic regression, C=0.7 (shipped) | 0.909 | 0.836 |
| Logistic regression, tuned C | 0.910 | 0.833 |
| Logistic regression, L1 | 0.907 | 0.837 |
| Logistic regression, splines | 0.909 | 0.827 |
| Random forest | 0.908 | 0.833 |
| Shallow boosting | 0.897 | 0.823 |
| SVM (rbf) | 0.899 | 0.802 |
| Average of LR + forest + SVM | 0.911 | 0.830 |

Differences of about 0.002 are within the run-to-run spread (standard deviation 0.003 to 0.005), so the honest
reading is that all the sensible models are tied. More complex models were equal or worse. The limit is the data
(303 patients, about 160 positive cases), not the algorithm. Swapping algorithms will not move this number.

## What would actually improve the model

1. **More and different patients.** The multi-site UCI file (920 patients, Cleveland, Hungary, Switzerland,
   VA Long Beach) is already readable by `core.load_raw()`. Put `heart_disease_uci.csv` in `data/` and run
   `python external_validation.py --data data/heart_disease_uci.csv`. It trains on Cleveland and scores each other
   hospital untouched, plus leave-one-site-out. That is the first real external test. Expect lower AUC than 0.91
   and calibration drift; Switzerland and the VA file are missing many vessel and thallium values.
2. **Modern data.** These patients were referred for angiography in the 1980s. Current populations differ in
   risk factors, treatment and test use, and women are under-represented (97 of 303).
3. **The right outcome.** The label is angiographic disease, not future heart attack or death.
4. **Prospective evaluation** with clinicians: does using the estimate change decisions and outcomes.

## What not to claim

An AUC says how well the model ranks patients in this dataset. It does not show that using the tool improves
care or saves lives. That needs prospective evidence, clinical oversight, and regulatory review before any
clinical use. Until then CardioSense is an educational research prototype.

## The first-visit model

Using only age, sex, chest-pain type, blood pressure, cholesterol, glucose and resting ECG gives AUC 0.84
(95% CI 0.79 to 0.88). This is the setting where a better tool could matter most, because it needs no
specialist tests, but it is also the least accurate. It is measured but is not yet offered in the app.
