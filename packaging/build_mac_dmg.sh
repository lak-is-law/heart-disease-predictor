#!/usr/bin/env bash
# ==============================================================================
# CardioSense Enterprise macOS DMG Builder
# Supports:
#   - Apple Silicon (arm64): M1, M2, M3, M4
#   - Intel (x86_64)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
VERSION="2.4.0"

# Architecture detection or argument override
TARGET_ARCH="${1:-$(uname -m)}"
if [ "$TARGET_ARCH" = "aarch64" ]; then
    TARGET_ARCH="arm64"
fi

echo "======================================================================"
echo " Building CardioSense Enterprise v${VERSION} for macOS [${TARGET_ARCH}]"
echo "======================================================================"

BUILD_DIR="${ROOT_DIR}/build"
DIST_DIR="${ROOT_DIR}/dist"
DMG_STAGING="${BUILD_DIR}/dmg_staging_${TARGET_ARCH}"
DMG_NAME="CardioSense-Enterprise-${VERSION}-macos-${TARGET_ARCH}.dmg"
DMG_OUT="${DIST_DIR}/${DMG_NAME}"

# Clean staging directory on exit or interruption
trap 'rm -rf "${DMG_STAGING}"' EXIT INT TERM

mkdir -p "${BUILD_DIR}"
mkdir -p "${DIST_DIR}"
rm -rf "${DMG_STAGING}"
mkdir -p "${DMG_STAGING}"

# Step 1: Run PyInstaller or assemble robust fallback bundle
echo "--> Compiling standalone binary with PyInstaller..."
export TARGET_ARCH="${TARGET_ARCH}"

if command -v pyinstaller &> /dev/null; then
    pyinstaller --clean --noconfirm \
        --distpath "${DIST_DIR}" \
        --workpath "${BUILD_DIR}" \
        "${SCRIPT_DIR}/CardioSense-mac.spec"
else
    echo "Warning: pyinstaller not found in PATH. Assembling self-contained mock .app bundle."
    APP_BUNDLE="${DIST_DIR}/CardioSense.app"
    CONTENTS_DIR="${APP_BUNDLE}/Contents"
    MACOS_DIR="${CONTENTS_DIR}/MacOS"
    RESOURCES_DIR="${CONTENTS_DIR}/Resources"

    mkdir -p "${MACOS_DIR}"
    mkdir -p "${RESOURCES_DIR}"

    # Generate Info.plist
    cat <<EOF > "${CONTENTS_DIR}/Info.plist"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>CardioSense</string>
    <key>CFBundleDisplayName</key>
    <string>CardioSense Enterprise</string>
    <key>CFBundleIdentifier</key>
    <string>com.cardiosense.enterprise</string>
    <key>CFBundleVersion</key>
    <string>${VERSION}</string>
    <key>CFBundleShortVersionString</key>
    <string>${VERSION}</string>
    <key>CFBundleExecutable</key>
    <string>CardioSense</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSApplicationCategoryType</key>
    <string>public.app-category.medical-software</string>
    <key>LSMinimumSystemVersion</key>
    <string>12.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF

    # Create robust POSIX shell launcher wrapper with proper shebang
    cat << 'LAUNCHER_EOF' > "${MACOS_DIR}/CardioSense"
#!/usr/bin/env bash
set -e
BUNDLE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RESOURCES_DIR="${BUNDLE_DIR}/Resources"
export PYTHONPATH="${RESOURCES_DIR}:${PYTHONPATH:-}"
exec python3 "${RESOURCES_DIR}/desktop_launcher.py" "$@"
LAUNCHER_EOF
    chmod +x "${MACOS_DIR}/CardioSense"

    # Stage runtime assets into Contents/Resources
    cp "${ROOT_DIR}/desktop_launcher.py" "${RESOURCES_DIR}/"
    cp "${ROOT_DIR}/app.py" "${RESOURCES_DIR}/"
    cp "${ROOT_DIR}/core.py" "${RESOURCES_DIR}/"
    cp "${ROOT_DIR}/cgi_heart.py" "${RESOURCES_DIR}/"
    cp "${ROOT_DIR}/requirements.txt" "${RESOURCES_DIR}/"

    if [ -d "${ROOT_DIR}/artifacts" ]; then cp -R "${ROOT_DIR}/artifacts" "${RESOURCES_DIR}/"; fi
    if [ -d "${ROOT_DIR}/data" ]; then cp -R "${ROOT_DIR}/data" "${RESOURCES_DIR}/"; fi
    if [ -d "${ROOT_DIR}/components" ]; then cp -R "${ROOT_DIR}/components" "${RESOURCES_DIR}/"; fi
    if [ -d "${ROOT_DIR}/portal" ]; then cp -R "${ROOT_DIR}/portal" "${RESOURCES_DIR}/"; fi
fi

# Step 2: Codesign application bundle
echo "--> Codesigning application bundle..."
SIGN_IDENTITY="${CODESIGN_IDENTITY:--}"
if command -v codesign &> /dev/null; then
    codesign --force --deep -s "${SIGN_IDENTITY}" "${DIST_DIR}/CardioSense.app" 2>/dev/null || {
        echo "Ad-hoc fallback signing..."
        codesign --force --deep -s - "${DIST_DIR}/CardioSense.app" 2>/dev/null || true
    }
fi

# Step 3: Assemble DMG staging directory with Applications symlink
echo "--> Assembling DMG staging directory..."
cp -R "${DIST_DIR}/CardioSense.app" "${DMG_STAGING}/"
ln -s /Applications "${DMG_STAGING}/Applications"

if [ -f "${ROOT_DIR}/packaging/assets/app_icon.icns" ]; then
    cp "${ROOT_DIR}/packaging/assets/app_icon.icns" "${DMG_STAGING}/.VolumeIcon.icns" 2>/dev/null || true
fi

# Step 4: Build UDZO read-only compressed DMG via hdiutil
echo "--> Creating compressed Apple Disk Image (.dmg)..."
rm -f "${DMG_OUT}"
if command -v hdiutil &> /dev/null; then
    hdiutil create \
        -volname "CardioSense Enterprise ${VERSION}" \
        -srcfolder "${DMG_STAGING}" \
        -ov \
        -format UDZO \
        "${DMG_OUT}"
    echo "DMG successfully created: ${DMG_OUT}"
else
    echo "Warning: hdiutil not found (non-macOS host). Creating compressed archive."
    tar -czf "${DMG_OUT}.tar.gz" -C "${DMG_STAGING}" .
    mv "${DMG_OUT}.tar.gz" "${DMG_OUT}"
fi

# Step 5: Compute SHA-256 Checksum
echo "--> Computing cryptographic digest..."
SHA=""
if command -v shasum &> /dev/null; then
    SHA=$(shasum -a 256 "${DMG_OUT}" | awk '{print $1}')
elif command -v sha256sum &> /dev/null; then
    SHA=$(sha256sum "${DMG_OUT}" | awk '{print $1}')
else
    SHA=$(python3 -c "import hashlib, sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" "${DMG_OUT}")
fi

echo "======================================================================"
echo " BUILD COMPLETE"
echo " File:       ${DMG_OUT}"
echo " Size:       $(du -h "${DMG_OUT}" | awk '{print $1}')"
echo " SHA-256:    ${SHA}"
echo "======================================================================"
echo "${SHA}  ${DMG_NAME}" > "${DIST_DIR}/${DMG_NAME}.sha256"
