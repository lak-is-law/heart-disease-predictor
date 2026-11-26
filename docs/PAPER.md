# Who needs the extra tests? Conformal triage with a first-visit model, and an audit of what 303 patients can support

*Working paper, CardioSense project. Internal validation only. Not peer reviewed. Not for clinical use.*

## Abstract

**Background.** Estimating the probability of coronary artery disease (CAD) usually needs an exercise test,
fluoroscopy and a nuclear scan. A model built only from first-visit data (age, sex, chest-pain type, blood
pressure, cholesterol, fasting glucose, resting ECG) is cheaper but less accurate. **Question.** Can a conformal
uncertainty estimate from the first-visit model decide which patients can be handled at the first visit and
which should be escalated to the full work-up, and what does it cost in accuracy? **Methods.** Cleveland
Heart Disease data (n=303, 139 with angiographic disease), logistic regression, repeated stratified
5-fold cross-validation with the conformal calibration set held out inside each training fold. **Results.** The
13-input model has out-of-fold AUC 0.91 (95% CI 0.87 to 0.94; bootstrap optimism-corrected 0.916) and the
first-visit model 0.84 (0.79 to 0.88). Seven other model families did not beat logistic regression by more than
run-to-run noise. Escalating only patients whose conformal set contains both classes let 34% of patients skip the
extra tests for a 1.5 percentage-point loss in accuracy (95% CI 0.7 to 2.4) and 60% skip them for a 3.0-point
loss (1.4 to 4.8), against sending everyone to the full work-up. A non-conformal probability band chosen to
escalate the same share made identical decisions, so the conformal wrapper adds a coverage guarantee and a
principled way to set the rate, not extra accuracy. **Conclusions.** In this small single-site sample, a
first-visit model can safely spare some patients the extra tests only at a measurable accuracy cost. The result
is internal; the central open question is whether it holds at other hospitals.

## 1. Motivation

Coronary artery disease is a leading cause of death worldwide, and diagnostic work-ups differ widely in cost and
access. Risk models matter most where specialist tests are scarce, which is exactly where a first-visit model is
used. But published tools are often reported with a single AUC from a single dataset, no uncertainty at the
patient level, and no statement of what the output means in a population with a different disease prevalence.
This project asks a narrow, testable question and reports the limits as results.

## 2. Data

UCI Heart Disease, Cleveland Clinic, Detrano et al. (1989); Janosi, Steinbrunn, Pfisterer, Detrano (1988),
CC BY 4.0. 303 patients referred for coronary angiography, ages 29 to 77, 97 women. Outcome: any angiographic
narrowing (original `num` greater than 0), present in 139 patients (45.9%; 25.8% of women, 55.3% of men). Six
patients lack the vessel count or thallium value and are median or mode imputed inside each training fold.
Inputs: 13 clinical variables (Section 4). The training population is a 1980s, single-site, referred sample.

## 3. Methods

**Models.** L2-penalised logistic regression (C=0.7) on standardised numeric and one-hot categorical inputs, for
the full 13-input set and the 7-input first-visit set. Comparators: tuned-C and L1 logistic regression, splines,
random forest, shallow boosting, SVM (benchmark.py).
**Validation.** 20 repeats of stratified 5-fold CV for headline AUC (evaluate.py), 6 to 10 repeats elsewhere;
bootstrap 95% intervals over patients; Harrell bootstrap optimism correction (200 resamples).
**Sample size.** Riley et al. (2020) criterion for shrinkage at least 0.9, using apparent Cox-Snell R squared.
**Utility.** Decision-curve net benefit (Vickers and Elkin 2006).
**Uncertainty.** Split-conformal classification (Vovk et al. 2005): within each training fold, 30% of patients
calibrate the nonconformity score; the prediction set contains every class whose score is within the
(1 - alpha) quantile.
**Triage policy.** If the first-visit conformal set has one class, accept it. Otherwise escalate and use the full
model at 0.5. Reference policy: everyone is escalated. Control: a central probability band with the same
escalation rate.
Code: `selective_escalation.py`, `rigor.py`, `benchmark.py`; figures: `make_figures.py`; seeds fixed.

## 4. Results

**Discrimination and calibration.** Full model AUC 0.910 (0.872 to 0.943), first-visit 0.836 (0.790 to 0.882)
(Fig. roc). Optimism-corrected AUC 0.916 and 0.842; bootstrap calibration slope 0.96 and 1.02 (Fig. calibration).
By sex, AUC was 0.93 in women (n=97, 25 cases, wide uncertainty) and 0.89 in men; below 55 years 0.93 and from 55
years 0.88.

**Model families.** No alternative exceeded the shipped logistic regression by more than 0.002 AUC (Table in
MODEL_REPORT.md). Flexible models were equal or worse, as expected with 139 events and 22 parameters.

**Sample size and learning curve.** The full model needs about 301 patients by the Riley criterion against 303
available (6.3 events per parameter); the first-visit model needs about 272. The 13-input learning curve was
still rising (AUC 0.90 at n=60 to 0.93 at n=240); the first-visit curve was flat near 0.84 (Fig. learning curve),
suggesting it is limited by missing predictors rather than patient numbers.

**Decision curve.** Acting on the full model has higher net benefit than treating everyone at every threshold
from 0.2 to 0.7 (0.345 versus 0.248 at 0.28; 0.297 versus -0.083 at 0.5) (Fig. decision curve), in a sample where
46% have disease.

**Selective escalation.** Reference (everyone gets the full work-up): accuracy 0.826, sensitivity 0.780,
specificity 0.866, 30.6 missed cases. (Fig. escalation)

| alpha | share who skip extra tests | accuracy | sensitivity | missed | accuracy change (95% CI) |
|---|---|---|---|---|---|
| 0.02 | 17% | 0.824 | 0.777 | 31.0 | -0.2 pt (-0.5, 0.0) |
| 0.05 | 34% | 0.812 | 0.768 | 32.2 | -1.5 pt (-2.4, -0.7) |
| 0.10 | 60% | 0.796 | 0.755 | 34.0 | -3.0 pt (-4.8, -1.4) |
| 0.15 | 80% | 0.783 | 0.745 | 35.5 | -4.4 pt (-7.1, -1.6) |

The band control produced the same accuracy and sensitivity at each rate. Above alpha 0.15 the escalation rate
stops falling because the conformal quantile is estimated from about 65 calibration patients.

## 5. Discussion

The useful finding is a quantified trade-off rather than a better model: roughly one third of patients can skip the
extra tests for about 1.5 points of accuracy, and the exchange rate worsens quickly beyond that. Conformal
prediction contributes the guarantee that coverage matches the chosen level and an interpretable dial, but in a
binary problem with a monotone score it selects the same patients as a probability band. The learning curves give
a testable prediction: more patients should improve the full model, while the first-visit model needs new
predictors (smoking, diabetes status, family history, BMI, lipid panel).

## 6. Limitations

1. One hospital, 1980s, referred patients: external complete-case coverage of 2/617 for the shipped model, unknown transport to current populations,
   ethnicities or to current practice. Prevalence is 46%, so probabilities overstate risk in screening populations.
2. The outcome is angiographic disease, not heart attack or death, and not a treatment decision.
3. The reference policy is the full model, not a clinician. Tests are assumed available when escalated; their cost
   and delay are not modelled.
4. Only 25 women with disease; subgroup estimates are imprecise and no fairness claim is made.
5. All intervals are internal. Repeated resampling of 303 patients understates uncertainty about new populations.
6. The reported sample-size check uses an approximation (apparent R squared times 0.9).

## 7. Ethics and intended use

Educational research prototype; not a medical device and not cleared by any regulator. It must not be used to
diagnose, rule out disease or choose treatment. Emergency symptoms need emergency care. The public site stores no
real patient data and asks users not to enter any. A clinical pathway would need prospective evaluation,
clinician oversight, local calibration and regulatory review. Whether any such tool reduces heart attacks is an
empirical question this study does not answer.

## 8. Reproducibility

`bash reproduce.sh` regenerates every number and figure from the Cleveland file in `data/` with fixed seeds
(roughly 15 to 25 minutes on 2 CPU cores). External validation needs the multi-site file and is run with
`external_validation.py`; no external result is reported here.

## References

- Detrano R, et al. International application of a new probability algorithm for the diagnosis of coronary artery disease. Am J Cardiol. 1989;64:304-310.
- Janosi A, Steinbrunn W, Pfisterer M, Detrano R. Heart Disease. UCI Machine Learning Repository. 1988. https://doi.org/10.24432/C52P4X
- Riley RD, et al. Calculating the sample size required for developing a clinical prediction model. BMJ. 2020;368:m441.
- Vickers AJ, Elkin EB. Decision curve analysis: a novel method for evaluating prediction models. Med Decis Making. 2006;26:565-574.
- Vovk V, Gammerman A, Shafer G. Algorithmic Learning in a Random World. Springer; 2005.
- Angelopoulos AN, Bates S. A gentle introduction to conformal prediction and distribution-free uncertainty quantification. arXiv:2107.07511. 2021.
- Collins GS, et al. Transparent reporting of a multivariable prediction model for individual prognosis or diagnosis (TRIPOD). Ann Intern Med. 2015;162:55-63.
- Harrell FE. Regression Modeling Strategies. 2nd ed. Springer; 2015.
