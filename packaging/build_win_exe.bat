@echo off
REM ==============================================================================
REM CardioSense Enterprise Windows Executable & Installer Builder
REM Supports:
REM   - Windows 10/11 64-bit (x64)
REM   - Windows ARM64 (Qualcomm Snapdragon X Elite)
REM ==============================================================================

set VERSION=2.4.0
set TARGET_ARCH=%1
if "%TARGET_ARCH%"=="" set TARGET_ARCH=x64

echo ======================================================================
echo  Building CardioSense Enterprise v%VERSION% for Windows [%TARGET_ARCH%]
echo ======================================================================

set SCRIPT_DIR=%~dp0
set ROOT_DIR=%SCRIPT_DIR%..
cd /d "%ROOT_DIR%"

mkdir build 2>nul
mkdir dist 2>nul

echo [1/3] Running PyInstaller packaging...
pyinstaller --clean --noconfirm packaging\CardioSense-win.spec

echo [2/3] Compiling Inno Setup Enterprise Installer...
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" packaging\installer_inno.iss
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    "C:\Program Files\Inno Setup 6\ISCC.exe" packaging\installer_inno.iss
) else (
    echo [WARNING] Inno Setup compiler ISCC.exe not found. Portable executable available in dist\CardioSense\
)

echo [3/3] Creating Portable Zip archive...
powershell -Command "Compress-Archive -Path dist\CardioSense -DestinationPath dist\CardioSense-Enterprise-%VERSION%-windows-%TARGET_ARCH%-portable.zip -Force"

echo ======================================================================
echo Windows Build Complete! Artifacts located in: %ROOT_DIR%\dist\
echo ======================================================================
