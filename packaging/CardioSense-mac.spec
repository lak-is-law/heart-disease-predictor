# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller specification for CardioSense macOS Application Bundle (.app)
Targets:
  - Apple Silicon (ARM64)
  - Intel x86_64
"""
import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Base project path
PROJECT_DIR = os.path.abspath(os.path.join(SPECPATH, ".."))

# Collect Streamlit static web assets and package data
streamlit_datas = collect_data_files("streamlit")
plotly_datas = collect_data_files("plotly")
sklearn_datas = collect_data_files("sklearn")

datas = [
    (os.path.join(PROJECT_DIR, "app.py"), "."),
    (os.path.join(PROJECT_DIR, "core.py"), "."),
    (os.path.join(PROJECT_DIR, "artifacts"), "artifacts"),
    (os.path.join(PROJECT_DIR, "data"), "data"),
    (os.path.join(PROJECT_DIR, "requirements.txt"), "."),
] + streamlit_datas + plotly_datas + sklearn_datas

hiddenimports = [
    "streamlit",
    "streamlit.web.cli",
    "plotly",
    "plotly.graph_objects",
    "sklearn",
    "sklearn.ensemble",
    "sklearn.linear_model",
    "sklearn.preprocessing",
    "sklearn.impute",
    "sklearn.pipeline",
    "sklearn.compose",
    "joblib",
    "numpy",
    "pandas",
    "xgboost",
    "webview",
] + collect_submodules("streamlit") + collect_submodules("sklearn")

a = Analysis(
    [os.path.join(PROJECT_DIR, "desktop_launcher.py")],
    pathex=[PROJECT_DIR],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "IPython", "notebook"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CardioSense",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=os.environ.get("TARGET_ARCH", None),  # "arm64" or "x86_64"
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="CardioSense",
)

app = BUNDLE(
    coll,
    name="CardioSense.app",
    icon=os.path.join(PROJECT_DIR, "packaging", "assets", "app_icon.icns") if os.path.exists(os.path.join(PROJECT_DIR, "packaging", "assets", "app_icon.icns")) else None,
    bundle_identifier="com.cardiosense.enterprise",
    info_plist={
        "CFBundleName": "CardioSense",
        "CFBundleDisplayName": "CardioSense Enterprise",
        "CFBundleIdentifier": "com.cardiosense.enterprise",
        "CFBundleVersion": "2.4.0",
        "CFBundleShortVersionString": "2.4.0",
        "NSHighResolutionCapable": "True",
        "LSMinimumSystemVersion": "12.0.0",
        "NSHumanReadableCopyright": "Copyright © 2026 American Express & CardioSense Enterprise. All rights reserved.",
    },
)
