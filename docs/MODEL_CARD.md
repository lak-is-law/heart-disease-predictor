# Model card: CardioSense risk model

Follows Mitchell et al. (2019). Educational research prototype, not a medical device.

| | |
|---|---|
| Model | L2 logistic regression (C=0.7), 22 parameters after one-hot encoding. Runs in the browser from `portal/model_weights.json`. |
| Variants | 13-input model (shipped). 7-input first-visit model (evaluated, not shipped). |
| Intended use | Teaching and research on risk estimation. Not for diagnosis, screening, triage of real patients or treatment decisions. |
| Out of scope | General-population screening, anyone under 18, emergency assessment, any use with real patient data. |
| Training data | UCI Heart Disease, Cleveland, n=303, 139 with disease. See DATASHEET.md. |
| Output | Probability that coronary angiography would show narrowing, among patients referred for angiography. Threshold 0.50 (standard) or 0.28 (high-sensitivity). |
| Performance (internal) | AUC 0.91 (0.87 to 0.94) for 13 inputs; 0.84 (0.79 to 0.88) first-visit. Sensitivity 0.885 and specificity 0.732 at 0.28; 0.79 and 0.88 at 0.50. Calibration slope 0.96. |
| Subgroups | AUC 0.93 in women (n=97, only 25 cases, imprecise), 0.89 in men; 0.93 under 55, 0.88 at 55 or over. No fairness claim. |
| External historical evaluation | Across Hungary, Switzerland and VA Long Beach, only 2/617 met all 13 input rules, both with disease. The seven-input research variant covered 361/617. See [site-specific results](rehearsal-validation.json). |
| Not measured | Indian outpatient performance, prospective performance, performance by ethnicity (not recorded), effect on outcomes. |
| Known failure modes | Probabilities too high when prevalence is lower than 46%. The workstation withholds scores for missing or invalid inputs. Age outside 29 to 77 is extrapolation. A low estimate does not rule out disease. |
| Ethical considerations | No real patient data should be entered. Output must not be presented as clinical advice. Sex differences in presentation are under-represented in the data. |
| Update policy | Retrain only with a documented dataset and rerun `bash reproduce.sh`; parity tests pin the exported weights. |
| Contact | Report a bug on the site. |
