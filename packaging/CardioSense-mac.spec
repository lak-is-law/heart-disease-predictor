# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller specification for CardioSense macOS Application Bundle (.app)
Targets:
  - Apple Silicon (ARM64: M1, M2, M3, M4)
  - Intel x86_64
"""
import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Base project path
PROJECT_DIR = os.path.abspath(os.path.join(SPECPATH, ".."))

# Collect Streamlit, Plotly, and scikit-learn package data
streamlit_datas = collect_data_files("streamlit")
plotly_datas = collect_data_files("plotly")
sklearn_datas = collect_data_files("sklearn")

# Comprehensive application data files and offline assets
raw_datas = [
    (os.path.join(PROJECT_DIR, "app.py"), "."),
    (os.path.join(PROJECT_DIR, "core.py"), "."),
    (os.path.join(PROJECT_DIR, "cgi_heart.py"), "."),
    (os.path.join(PROJECT_DIR, "requirements.txt"), "."),
    (os.path.join(PROJECT_DIR, "artifacts"), "artifacts"),
    (os.path.join(PROJECT_DIR, "data"), "data"),
    (os.path.join(PROJECT_DIR, "components"), "components"),
    (os.path.join(PROJECT_DIR, "portal", "vendor"), "portal/vendor"),
    (os.path.join(PROJECT_DIR, "portal", "model_weights.json"), "portal"),
    (os.path.join(PROJECT_DIR, "portal", "manifest.json"), "portal"),
]

# Filter existing files only
datas = [item for item in raw_datas if os.path.exists(item[0])] + streamlit_datas + plotly_datas + sklearn_datas

hiddenimports = [
    "streamlit",
    "streamlit.web.cli",
    "streamlit.runtime.scriptrunner.magic_expressions",
    "streamlit.elements.lib.column_types",
    "cgi_heart",
    "core",
    "components",
    "components.lab_report_parser",
    "plotly",
    "plotly.graph_objects",
    "sklearn",
    "sklearn.ensemble",
    "sklearn.linear_model",
    "sklearn.preprocessing",
    "sklearn.impute",
    "sklearn.pipeline",
    "sklearn.compose",
    "scipy",
    "scipy.special",
    "joblib",
    "numpy",
    "pandas",
    "xgboost",
    "webview",
] + collect_submodules("streamlit") + collect_submodules("sklearn") + collect_submodules("plotly")

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

icon_path = os.path.join(PROJECT_DIR, "packaging", "assets", "app_icon.icns")

app = BUNDLE(
    coll,
    name="CardioSense.app",
    icon=icon_path if os.path.exists(icon_path) else None,
    bundle_identifier="com.cardiosense.enterprise",
    info_plist={
        "CFBundleName": "CardioSense",
        "CFBundleDisplayName": "CardioSense Enterprise",
        "CFBundleIdentifier": "com.cardiosense.enterprise",
        "CFBundleVersion": "2.4.0",
        "CFBundleShortVersionString": "2.4.0",
        "CFBundleExecutable": "CardioSense",
        "CFBundlePackageType": "APPL",
        "LSApplicationCategoryType": "public.app-category.medical-software",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "12.0.0",
        "NSRequiresAquaSystemAppearance": False,
        "NSHumanReadableCopyright": "Copyright © 2026 American Express & CardioSense Enterprise. All rights reserved.",
    },
)
