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
(303 patients, 139 positive cases), not the algorithm. Swapping algorithms will not move this number.

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

## Rigour checks (`python rigor.py`, writes `artifacts/rigor.json`)

Internal validation on Cleveland, 303 patients, 139 with angiographic disease.

| Check | 13 inputs | First-visit (7 inputs) |
|---|---|---|
| Apparent AUC | 0.935 | 0.858 |
| Optimism-corrected AUC (bootstrap, 200) | 0.916 | 0.842 |
| Calibration slope (bootstrap) | 0.96 | 1.02 |
| Events per parameter | 6.3 | 11.6 |
| Minimum n for shrinkage 0.9 (Riley) vs actual 303 | 301 | 272 |
| Conformal 90%: share of patients the model should call "uncertain" | 20% | 40% |
| Conformal 90%: accuracy on the remaining confident patients | 0.89 | 0.84 |

What this says:

1. **The reported AUC is honest for this dataset.** About 0.02 of the apparent AUC is overfitting. The corrected value (0.916) agrees with cross-validation (0.91). Calibration is close to ideal.
2. **The full model is only just big enough.** It meets the minimum sample size by a hair, with 6.3 events per parameter. The first-visit model has more margin. Neither has room for a more complex model, which is why flexible models did not help.
3. **The two models are limited by different things.** The 13-input learning curve (AUC 0.90 at n=60 to 0.93 at n=240) is still rising, so more patients would probably help it. The first-visit curve is flat near 0.84 from n=120, so more patients alone would not help it; it needs new predictors that Cleveland does not have, such as smoking, diabetes status, family history, BMI and a full lipid panel. The curves are noisy and cap at 240 training patients, so this is suggestive, not proof.
4. **Acting on the estimate beats the alternatives in this population.** Decision-curve net benefit for the 13-input model is higher than treating everyone at every threshold from 0.2 to 0.7 (for example 0.345 vs 0.248 at 0.28, and 0.297 vs -0.083 at 0.5). At 0.1 it is about equal to treating everyone. This holds only for patients already referred for angiography, where 46% have disease.
5. **The probabilities do not transfer to screening.** Because 46% of this sample has disease, the model's probabilities will be far too high in a general or primary-care population where prevalence is a few percent. The output means "among patients like those referred for angiography", and the app should say so wherever it shows a percentage.
6. **A "model is unsure" flag is feasible.** Split-conformal prediction achieved its target 90% coverage (0.906 and 0.901). It would label 20% of patients uncertain for the full model, with 89% accuracy on the rest, and 40% for the first-visit model (84% on the rest). Showing it is not yet implemented in the app.
