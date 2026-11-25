# CardioSense

**Research question.** A first-visit heart-disease risk model is cheap but less accurate than one that needs a stress test,
fluoroscopy and a nuclear scan. Can conformal uncertainty decide who can skip the extra tests, and at what cost?

**Answer (internal validation, 303 patients).** About one third of patients can skip the extra tests for a 1.5 point loss in
accuracy; 60% for 3 points. No model family beat logistic regression (AUC 0.91, or 0.84 with first-visit inputs). More data
should help the full model; the first-visit model needs new predictors. External validity is untested.

| Read | |
|---|---|
| [docs/PAPER.md](docs/PAPER.md) | Working paper: methods, results, limitations, ethics |
| [docs/MODEL_CARD.md](docs/MODEL_CARD.md), [docs/DATASHEET.md](docs/DATASHEET.md) | Model card and datasheet |
| [docs/MODEL_REPORT.md](docs/MODEL_REPORT.md) | Benchmark and rigour checks |
| `bash reproduce.sh` | Regenerates every number and figure |
| `external_validation.py` | Train on Cleveland, test on other hospitals (needs the multi-site file) |

**Not a medical device and not for clinical use.** Whether a tool like this reduces heart attacks is an open empirical
question that needs prospective evidence, clinician oversight and regulatory review.

---

# CardioSense AI

[![Vercel Deployment](https://img.shields.io/badge/Vercel-Live%20Demo-black?logo=vercel)](https://heart-disease-predictor-kohl-nine.vercel.app)
[![GitHub Repository](https://img.shields.io/badge/GitHub-Repository-blue?logo=github)](https://github.com/lak-is-law/heart-disease-predictor)

> **Live Web Application & Distribution Portal:**  
> **[https://heart-disease-predictor-kohl-nine.vercel.app](https://heart-disease-predictor-kohl-nine.vercel.app)**

Logistic Regression, Random Forest and XGBoost trained on the UCI Heart Disease data, wrapped in an
an interactive 3D heart, a lab report parser and a download portal.

**Research prototype. Not for clinical use. Not a medical device.** See Limitations below.

## Run it

```bash
pip install -r requirements.txt

# 1) Data (pick one, or skip and let train.py download the Cleveland file from UCI)
#    Kaggle: https://www.kaggle.com/datasets/redwankarimsony/heart-disease-data
#    -> save heart_disease_uci.csv into ./data/

# 2) Train (creates artifacts/heart_model.joblib)
python train.py                         # auto-detects ./data or downloads from UCI
python train.py --cleveland-only        # restrict the Kaggle file to the 303-patient Cleveland subset
python train.py --data path/to/file.csv

# 3) Launch the UI
streamlit run app.py
```

## Project layout

| File | Purpose |
|---|---|
| `core.py` | data loading and normalisation, preprocessing pipeline, model factory, prediction and explanation |
| `train.py` | cross-validation, hold-out evaluation, permutation importance, saves the artifacts |
| `app.py` | Streamlit UI (risk assessment, model lab, about, desktop downloads) |
| `desktop_launcher.py` | Native desktop launcher running Streamlit headlessly in a desktop frame |
| `portal/` | Clinical decision support workstation and 18-package architecture distribution hub |
| `packaging/` | PyInstaller specs, macOS DMG builder, Windows Inno Setup scripts, manifest generator |
| `artifacts/` | trained models and `metrics.json` (created by `train.py`) |

## Desktop Distribution (18 Granular Architectures)

CardioSense AI is packaged as native standalone desktop executables (`.dmg` for macOS, `.exe`/`.msi` for Windows, and `.tar.gz` for Linux), covering granular processor generations:
- **macOS (7 builds):** Apple Silicon M4, M3, M2, M1, Intel 10th Gen Core, Intel Xeon W Workstation, and Intel Legacy 64-bit.
- **Windows (8 builds):** Intel Core Ultra (Series 1 & 2), Intel 12th/13th Gen, AMD Ryzen Zen 4/5, Universal x64 Baseline, Zero-Install Portable, Snapdragon X Elite Copilot+, Snapdragon 8cx Gen 3, and Windows Server Enterprise Edition.
- **Linux (3 builds):** Enterprise HPC (AVX-512), Universal (SSE4.2), and ARM64 Server.

### Building Desktop Packages

- **Build macOS DMG (Apple Silicon or Intel):**
  ```bash
  bash packaging/build_mac_dmg.sh arm64   # for Apple Silicon
  bash packaging/build_mac_dmg.sh x86_64  # for Intel Macs
  ```

- **Build Windows Executable & Installer:**
  ```cmd
  call packaging\build_win_exe.bat x64
  ```

- **Run Native Desktop Client Locally:**
  ```bash
  python desktop_launcher.py
  ```

## Download portal

The portal in `portal/` detects the visitor's operating system and processor, lists the matching installers with SHA-256 checksums, and includes an in-browser checksum verifier. Sign-in, saved assessments and the dashboard are served by the functions in `api/` (see `docs/DEPLOY.md`).

```bash
python serve_portal.py --port 8080
```

## Limitations

- The model is trained on the UCI Cleveland data: 303 patients from one clinic in the 1980s, all referred for angiography, 97 of them women. The label is angiographic disease, not future events.
- Measured on repeated cross-validation, ROC AUC is 0.91 (95% CI 0.87 to 0.94) with all 13 inputs, but 0.84 (0.79 to 0.88) when the invasive and stress-test inputs are left out; see `artifacts/validation.json` and `evaluate.py`. The 13-input model needs fluoroscopy and thallium results, so it does not apply to a first visit, and the 0.91 figure is optimistic for that reason.
- It has not been tested prospectively or at any other site. Good AUC does not show that using it improves outcomes.
- A low estimate does not rule out disease. The 0.28 threshold gives about 88% sensitivity in cross-validation and flags many patients without disease.
- No regulatory clearance, exemption or compliance certification is claimed. Use only synthetic or de-identified data.

## Notes

- Supported inputs: UCI `processed.cleveland.data`, or Kaggle's `heart_disease_uci.csv`. Other mirrors
  that use a `target` column with different codings are not supported.
- The best model is chosen by cross-validated ROC AUC on the training split; test metrics come from a
  separate 20% hold-out.
- If `xgboost` is not installed, scikit-learn's gradient boosting is used in its place.
- Educational project only. It is not a medical device.
