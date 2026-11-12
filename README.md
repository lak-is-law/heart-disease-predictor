# CardioSense: Heart Disease Prediction System

[![Vercel Deployment](https://img.shields.io/badge/Vercel-Live%20Demo-black?logo=vercel)](https://heart-disease-predictor-kohl-nine.vercel.app)
[![GitHub Repository](https://img.shields.io/badge/GitHub-Repository-blue?logo=github)](https://github.com/lak-is-law/heart-disease-predictor)

> **Live Web Application & Enterprise Download Portal:**  
> 🔗 **[https://heart-disease-predictor-kohl-nine.vercel.app](https://heart-disease-predictor-kohl-nine.vercel.app)**

Logistic Regression, Random Forest and XGBoost trained on the UCI Heart Disease data, wrapped in an
interactive 3D CGI anatomical heart biomechanics laboratory and an American Express-styled desktop distribution portal.

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
| `serve_portal.py` | Local web server for the American Express-themed client download portal |
| `portal/` | Reverse-engineered American Express (Amex) UI/UX enterprise download center |
| `packaging/` | PyInstaller specs, macOS DMG builder, Windows Inno Setup scripts, manifest generator |
| `artifacts/` | trained models and `metrics.json` (created by `train.py`) |

## Desktop Distribution & Oracle Multi-Chip Matrix

CardioSense is packaged as native standalone desktop executables (`.dmg` for macOS and `.exe` for Windows), mirroring the multi-architecture distribution models used by enterprise platforms like Oracle:

| Operating System | Processor / Chipset | Package Format | Binary File |
|---|---|---|---|
| **macOS** | Apple Silicon (M1 / M2 / M3 / M4 - ARM64) | Apple Disk Image (`.dmg`) | `CardioSense-Enterprise-2.4.0-macos-arm64.dmg` |
| **macOS** | Intel 64-bit (x86_64) | Apple Disk Image (`.dmg`) | `CardioSense-Enterprise-2.4.0-macos-x64.dmg` |
| **Windows** | Intel / AMD 64-bit (x64) | Inno Setup Installer (`.exe`) | `CardioSense-Enterprise-2.4.0-windows-x64-Setup.exe` |
| **Windows** | Intel / AMD 64-bit (x64) | Zero-Install Portable (`.exe`) | `CardioSense-Enterprise-2.4.0-windows-x64-portable.exe` |
| **Windows** | ARM64 (Qualcomm Snapdragon X Elite) | Inno Setup Installer (`.exe`) | `CardioSense-Enterprise-2.4.0-windows-arm64-Setup.exe` |

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

## American Express (Amex) Reverse-Engineered Download Portal

The download portal in `portal/` has been reverse-engineered from the American Express Design Language System (DLS):
- **Visual Design:** Authentic Amex Primary Action Blue (`#006FCF`), Deep Midnight Navy (`#00175A`), Centurion gold accents (`#C5A059`), and crisp white card containers (`#D5D8DC` borders).
- **Client Auto-Detection:** Automatically inspects client processor architecture (Apple Silicon vs Intel vs Windows x64 vs ARM64) and displays a personalized recommendation card with 1-click download.
- **Oracle-Style Tabbed Matrix:** Filter by macOS, Windows, Linux, and Master Checksum tables.
- **Live In-Browser SHA-256 Verifier:** Drag-and-drop downloaded `.dmg` or `.exe` files into the browser; uses the client-side Web Crypto API to compute authentic SHA-256 digests and display a verified seal.
- **IT Deployment Guides:** Silent installation command-line flags and macOS Gatekeeper bypass commands.

### Launching the Amex Download Portal

```bash
python serve_portal.py --port 8080
```
Open [http://localhost:8080](http://localhost:8080) to view the live American Express download center.

## Notes

- Supported inputs: UCI `processed.cleveland.data`, or Kaggle's `heart_disease_uci.csv`. Other mirrors
  that use a `target` column with different codings are not supported.
- The best model is chosen by cross-validated ROC AUC on the training split; test metrics come from a
  separate 20% hold-out.
- If `xgboost` is not installed, scikit-learn's gradient boosting is used in its place.
- Educational project only. It is not a medical device.
