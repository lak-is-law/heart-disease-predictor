# Datasheet: UCI Heart Disease, Cleveland subset

Follows Gebru et al. (2021).

- **Motivation.** Collected to evaluate a probability algorithm for CAD diagnosis (Detrano et al. 1989). Used here for teaching and research on prediction.
- **Composition.** 303 patients, 14 attributes (13 predictors and outcome `num` 0 to 4, binarised as any narrowing). 97 women (25.8% with disease), 206 men (55.3%). Ages 29 to 77. Missing: 4 vessel counts, 2 thallium values. No names or direct identifiers.
- **Collection.** Patients referred for coronary angiography at the Cleveland Clinic, 1980s. Selection is by referral, so prevalence (45.9%) is far above any screening population.
- **Preprocessing.** Median and most-frequent imputation and standardisation inside each training fold (never on test data); one-hot encoding of chest-pain type, resting ECG, ST slope and thallium.
- **Uses.** Appropriate: methodological work, teaching, baselines. Inappropriate: clinical decisions, screening, claims about current populations or any ethnic group (not recorded).
- **Distribution.** Public, UCI Machine Learning Repository, CC BY 4.0, https://doi.org/10.24432/C52P4X. Cite Janosi, Steinbrunn, Pfisterer, Detrano (1988).
- **Maintenance.** Static historical dataset. The multi-site version (Hungary, Switzerland, VA Long Beach) is supported by `core.py` and `external_validation.py` but is not included in this repository.
