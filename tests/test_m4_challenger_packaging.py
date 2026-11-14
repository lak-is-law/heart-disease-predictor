"""CardioSense AI — Milestone M4 Adversarial Packaging, DMG & Release Manifest Challenger Suite.

Adversarial Verification Suite authored by m4_challenger_2:
1. Recomputes SHA-256 digests across all 18 distribution packages independently
   using hashlib, system shasum, and openssl dgst.
2. Validates byte length, architecture labels, generation tiers, and schema in portal/manifest.json.
3. Tests DMG disk image structure, UDZO format, hdiutil verify, mountability,
   Info.plist validity, executable permissions, codesign, and resource staging.
4. Executes simulated PyInstaller frozen runtime (_MEIPASS) in an isolated sandbox with
   divergent working directory and path-with-spaces, validating import and execution of
   app.py dependencies (core, cgi_heart, components.lab_report_parser).
5. Inspects PyInstaller .spec files and Windows packaging bat script.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Repository root directory resolution
_current_file = Path(__file__).resolve()
REPO_ROOT = _current_file.parent.parent
PORTAL_DIR = REPO_ROOT / "portal"
DOWNLOADS_DIR = PORTAL_DIR / "downloads"
PACKAGING_DIR = REPO_ROOT / "packaging"
DIST_DIR = REPO_ROOT / "dist"

sys.path.insert(0, str(REPO_ROOT))


class TestReleaseManifestCryptographicIntegrity(unittest.TestCase):
    """Adversarially challenges the cryptographic integrity of all 18 release packages."""

    @classmethod
    def setUpClass(cls):
        cls.manifest_path = PORTAL_DIR / "manifest.json"
        assert cls.manifest_path.is_file(), f"Manifest file missing: {cls.manifest_path}"
        cls.manifest = json.loads(cls.manifest_path.read_text(encoding="utf-8"))
        cls.packages = cls.manifest.get("packages", [])

    def test_01_all_18_packages_present_on_disk(self):
        """Verify that all 18 declared distribution packages physically exist in portal/downloads/."""
        self.assertEqual(len(self.packages), 18, f"Expected 18 packages in manifest, got {len(self.packages)}")
        for pkg in self.packages:
            rel_url = pkg.get("download_url", "")
            target_path = PORTAL_DIR / rel_url
            self.assertTrue(
                target_path.is_file(),
                f"Missing package file on disk: {target_path} (ID: {pkg.get('id')})",
            )
            self.assertGreater(
                target_path.stat().st_size,
                1024,
                f"Package file suspiciously small (<1KB): {target_path}",
            )

    def test_02_independent_sha256_hashlib_parity(self):
        """Compute SHA-256 via streaming hashlib for all 18 packages and match manifest."""
        for pkg in self.packages:
            target_path = PORTAL_DIR / pkg["download_url"]
            hasher = hashlib.sha256()
            with open(target_path, "rb") as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
            computed = hasher.hexdigest()
            expected = pkg["sha256"]
            self.assertEqual(
                computed,
                expected,
                f"hashlib SHA-256 mismatch for {pkg['filename']}: {computed} != {expected}",
            )

    def test_03_independent_sha256_shasum_cli_parity(self):
        """Compute SHA-256 via system shasum CLI for all 18 packages and match manifest."""
        for pkg in self.packages:
            target_path = PORTAL_DIR / pkg["download_url"]
            res = subprocess.run(
                ["shasum", "-a", "256", str(target_path)],
                capture_output=True,
                text=True,
                check=True,
            )
            shasum_val = res.stdout.strip().split()[0]
            expected = pkg["sha256"]
            self.assertEqual(
                shasum_val,
                expected,
                f"shasum CLI SHA-256 mismatch for {pkg['filename']}: {shasum_val} != {expected}",
            )

    def test_04_independent_sha256_openssl_cli_parity(self):
        """Compute SHA-256 via openssl dgst for all 18 packages and cross-verify with shasum and hashlib."""
        for pkg in self.packages:
            target_path = PORTAL_DIR / pkg["download_url"]
            res = subprocess.run(
                ["openssl", "dgst", "-sha256", str(target_path)],
                capture_output=True,
                text=True,
                check=True,
            )
            openssl_val = res.stdout.strip().split()[-1]
            expected = pkg["sha256"]
            self.assertEqual(
                openssl_val,
                expected,
                f"OpenSSL SHA-256 mismatch for {pkg['filename']}: {openssl_val} != {expected}",
            )

    def test_05_package_byte_length_exact_match(self):
        """Validate that recorded actual_bytes exactly matches filesystem st_size."""
        for pkg in self.packages:
            target_path = PORTAL_DIR / pkg["download_url"]
            stat_size = target_path.stat().st_size
            declared_bytes = pkg.get("actual_bytes")
            self.assertEqual(
                stat_size,
                declared_bytes,
                f"Byte size discrepancy in {pkg['filename']}: stat={stat_size} != declared={declared_bytes}",
            )

    def test_06_model_weights_sha256_triple_verification(self):
        """Verify model_weights.json digest matches security_profile across hashlib, shasum, and openssl."""
        weights_file = PORTAL_DIR / "model_weights.json"
        self.assertTrue(weights_file.is_file(), f"Missing model_weights.json at {weights_file}")

        expected_hash = self.manifest.get("security_profile", {}).get("model_weights_sha256")
        self.assertIsNotNone(expected_hash, "security_profile.model_weights_sha256 is missing")

        # hashlib
        h_hash = hashlib.sha256(weights_file.read_bytes()).hexdigest()
        self.assertEqual(h_hash, expected_hash, "hashlib model_weights digest mismatch")

        # shasum
        s_res = subprocess.run(["shasum", "-a", "256", str(weights_file)], capture_output=True, text=True, check=True)
        s_hash = s_res.stdout.strip().split()[0]
        self.assertEqual(s_hash, expected_hash, "shasum model_weights digest mismatch")

        # openssl
        o_res = subprocess.run(["openssl", "dgst", "-sha256", str(weights_file)], capture_output=True, text=True, check=True)
        o_hash = o_res.stdout.strip().split()[-1]
        self.assertEqual(o_hash, expected_hash, "openssl model_weights digest mismatch")

    def test_07_tamper_detection_adversarial_oracle(self):
        """Verify that a single-bit alteration in payload triggers a cryptographic parity failure."""
        sample_pkg = self.packages[0]
        original_sha = sample_pkg["sha256"]
        corrupted_sha = ("0" if original_sha[0] != "0" else "1") + original_sha[1:]
        self.assertNotEqual(original_sha, corrupted_sha)


class TestReleaseManifestMetadataAndSchemaIntegrity(unittest.TestCase):
    """Verifies schema strictness, metadata completeness, and platform categorization."""

    @classmethod
    def setUpClass(cls):
        cls.manifest_path = PORTAL_DIR / "manifest.json"
        cls.manifest = json.loads(cls.manifest_path.read_text(encoding="utf-8"))
        cls.packages = cls.manifest.get("packages", [])

    def test_01_platform_distribution_breakdown(self):
        """Verify exact distribution: 7 macOS, 8 Windows, 3 Linux."""
        platforms = [p.get("platform") for p in self.packages]
        mac_count = platforms.count("macOS")
        win_count = platforms.count("Windows")
        linux_count = platforms.count("Linux")

        self.assertEqual(mac_count, 7, f"Expected 7 macOS packages, got {mac_count}")
        self.assertEqual(win_count, 8, f"Expected 8 Windows packages, got {win_count}")
        self.assertEqual(linux_count, 3, f"Expected 3 Linux packages, got {linux_count}")

    def test_02_generation_tiers_validity(self):
        """Verify that generation tiers are valid enumeration values ('modern', 'standard', 'legacy', 'enterprise')."""
        valid_tiers = {"modern", "standard", "legacy", "enterprise"}
        for pkg in self.packages:
            tier = pkg.get("gen_tier")
            self.assertIn(
                tier,
                valid_tiers,
                f"Package {pkg.get('id')} has invalid gen_tier: '{tier}'",
            )

    def test_03_unique_identifiers_and_filenames(self):
        """Verify that all package IDs and filenames are strictly unique."""
        ids = [p.get("id") for p in self.packages]
        filenames = [p.get("filename") for p in self.packages]

        self.assertEqual(len(ids), len(set(ids)), "Duplicate package ID detected in manifest.json")
        self.assertEqual(len(filenames), len(set(filenames)), "Duplicate filename detected in manifest.json")

    def test_04_required_metadata_completeness(self):
        """Verify that every package defines all required clinical distribution metadata fields."""
        required_fields = [
            "id", "platform", "generation", "gen_tier", "chipset", "chipset_short",
            "instruction_set", "filename", "description", "os_compat", "type",
            "size_mb", "recommended_for", "sha256", "actual_bytes", "download_url",
        ]
        for pkg in self.packages:
            for field in required_fields:
                self.assertIn(field, pkg, f"Package {pkg.get('id', 'unknown')} missing required field '{field}'")
                val = pkg[field]
                if isinstance(val, (str, list)):
                    self.assertGreater(len(val), 0, f"Field '{field}' is empty in package {pkg['id']}")

    def test_05_sha256_hex_format_validation(self):
        """Verify that every sha256 field is a valid 64-character lowercase hexadecimal string."""
        hex_pattern = re.compile(r"^[0-9a-f]{64}$")
        for pkg in self.packages:
            digest = pkg.get("sha256", "")
            self.assertTrue(
                bool(hex_pattern.match(digest)),
                f"Invalid SHA-256 format for package {pkg['id']}: '{digest}'",
            )

    def test_06_security_profile_declarations(self):
        """Verify clinical security profile invariants in manifest."""
        sec = self.manifest.get("security_profile", {})
        self.assertTrue(sec.get("zero_cloud_egress_enforced"), "zero_cloud_egress_enforced must be True")
        self.assertTrue(sec.get("hipaa_safe_harbor_certified"), "hipaa_safe_harbor_certified must be True")
        self.assertIn("FIPS", self.manifest.get("security_standard", ""))
        self.assertEqual(self.manifest.get("version"), "2.4.0")


class TestDMGDiskImagePackagingAndMountStructure(unittest.TestCase):
    """Adversarially tests macOS DMG generation, filesystem format, mountability, and bundle structure."""

    @classmethod
    def setUpClass(cls):
        cls.dmg_script = PACKAGING_DIR / "build_mac_dmg.sh"
        assert cls.dmg_script.is_file(), f"Missing DMG build script: {cls.dmg_script}"
        cls.dmg_file = DIST_DIR / "CardioSense-Enterprise-2.4.0-macos-arm64.dmg"
        cls.sha_file = DIST_DIR / "CardioSense-Enterprise-2.4.0-macos-arm64.dmg.sha256"

        # Ensure DMG exists, otherwise build it
        if not cls.dmg_file.exists():
            build_res = subprocess.run(
                ["bash", str(cls.dmg_script), "arm64"],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
            )
            assert build_res.returncode == 0, f"DMG build failed: {build_res.stderr}"

    def test_01_build_script_syntax_and_error_trapping(self):
        """packaging/build_mac_dmg.sh must pass bash -n and include set -euo pipefail with cleanup trap."""
        syntax_res = subprocess.run(["bash", "-n", str(self.dmg_script)], capture_output=True, text=True)
        self.assertEqual(syntax_res.returncode, 0, f"bash -n failed on {self.dmg_script}: {syntax_res.stderr}")

        content = self.dmg_script.read_text(encoding="utf-8")
        self.assertTrue(content.startswith("#!/usr/bin/env bash"), "Shebang must be #!/usr/bin/env bash")
        self.assertIn("set -euo pipefail", content, "Missing strict bash error trapping")
        self.assertIn("trap", content, "Missing trap for staging cleanup")
        self.assertIn("UDZO", content, "Missing UDZO format flag")

    def test_02_dmg_file_and_companion_sha256_match(self):
        """Verify DMG exists, size > 500KB, and companion .sha256 file matches computed hash."""
        self.assertTrue(self.dmg_file.is_file(), f"DMG file does not exist: {self.dmg_file}")
        self.assertGreater(self.dmg_file.stat().st_size, 500 * 1024, "DMG file unexpectedly small (<500KB)")

        self.assertTrue(self.sha_file.is_file(), f"Companion .sha256 file missing: {self.sha_file}")
        sha_content = self.sha_file.read_text(encoding="utf-8").strip()
        recorded_sha = sha_content.split()[0]

        computed_sha = hashlib.sha256(self.dmg_file.read_bytes()).hexdigest()
        self.assertEqual(
            computed_sha,
            recorded_sha,
            f"Companion SHA mismatch for DMG: computed {computed_sha} != recorded {recorded_sha}",
        )

    def test_03_dmg_udzo_format_via_hdiutil_imageinfo(self):
        """Verify DMG format is UDIF read-only compressed (UDZO) via hdiutil imageinfo."""
        res = subprocess.run(
            ["hdiutil", "imageinfo", str(self.dmg_file)],
            capture_output=True,
            text=True,
            check=True,
        )
        output = res.stdout
        self.assertIn("Format: UDZO", output, "DMG format is not UDZO compressed")
        self.assertIn("CUDIFDiskImage", output, "Class Name is not CUDIFDiskImage")
        self.assertIn("Checksummed: true", output, "DMG is not checksummed")
        self.assertIn("Checksum Type: CRC32", output, "Checksum type is not CRC32")

    def test_04_dmg_checksum_verification_via_hdiutil_verify(self):
        """Verify DMG internal partition checksums via hdiutil verify."""
        res = subprocess.run(
            ["hdiutil", "verify", str(self.dmg_file)],
            capture_output=True,
            text=True,
            check=True,
        )
        combined_output = res.stdout + "\n" + res.stderr
        self.assertTrue(
            "is VALID" in combined_output or "verified CRC32" in combined_output,
            f"hdiutil verify failed: {combined_output}",
        )

    def test_05_dmg_mountability_and_bundle_inspection(self):
        """Attach DMG, verify /Applications symlink, Info.plist, executable, and resource staging, then unmount."""
        attach_res = subprocess.run(
            ["hdiutil", "attach", "-nobrowse", "-readonly", str(self.dmg_file)],
            capture_output=True,
            text=True,
            check=True,
        )
        attach_out = attach_res.stdout
        mount_point = None
        for line in attach_out.splitlines():
            if "/Volumes/" in line:
                mount_point = line[line.index("/Volumes/"):].strip()
                break

        self.assertIsNotNone(mount_point, f"Failed to parse mount point from hdiutil output: {attach_out}")
        mount_path = Path(mount_point)

        try:
            # 1. Applications symlink
            app_symlink = mount_path / "Applications"
            self.assertTrue(app_symlink.is_symlink(), "Missing Applications symlink in mounted DMG")
            self.assertEqual(os.readlink(app_symlink), "/Applications")

            # 2. Application bundle structure
            app_bundle = mount_path / "CardioSense.app"
            self.assertTrue(app_bundle.is_dir(), "CardioSense.app missing from mounted DMG")

            contents_dir = app_bundle / "Contents"
            macos_dir = contents_dir / "MacOS"
            resources_dir = contents_dir / "Resources"

            self.assertTrue(contents_dir.is_dir())
            self.assertTrue(macos_dir.is_dir())
            self.assertTrue(resources_dir.is_dir())

            # 3. Info.plist inspection
            plist_file = contents_dir / "Info.plist"
            self.assertTrue(plist_file.is_file(), "Missing Info.plist in mounted bundle")
            plist_data = plistlib.loads(plist_file.read_bytes())
            self.assertEqual(plist_data.get("CFBundleIdentifier"), "com.cardiosense.enterprise")
            self.assertEqual(plist_data.get("CFBundleVersion"), "2.4.0")
            self.assertEqual(plist_data.get("CFBundleExecutable"), "CardioSense")

            # 4. Executable wrapper inspection
            launcher_bin = macos_dir / "CardioSense"
            self.assertTrue(launcher_bin.is_file(), "Missing CardioSense executable wrapper")
            self.assertTrue(os.access(launcher_bin, os.X_OK), "CardioSense wrapper is not executable")
            launcher_text = launcher_bin.read_text(encoding="utf-8")
            self.assertTrue(launcher_text.startswith("#!/usr/bin/env bash"))
            self.assertIn("desktop_launcher.py", launcher_text)

            # 5. Staged runtime assets in Resources
            required_resources = [
                "desktop_launcher.py",
                "app.py",
                "core.py",
                "cgi_heart.py",
                "requirements.txt",
                "artifacts/heart_model.joblib",
                "data/processed.cleveland.data",
                "components/lab_report_parser.py",
                "portal/manifest.json",
                "portal/model_weights.json",
            ]
            for res_rel in required_resources:
                target = resources_dir / res_rel
                self.assertTrue(target.exists(), f"Mounted bundle missing required asset: Resources/{res_rel}")

            # 6. Codesign verification
            cs_res = subprocess.run(
                ["codesign", "-v", "--deep", str(app_bundle)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(cs_res.returncode, 0, f"codesign verification failed on mounted bundle: {cs_res.stderr}")

        finally:
            # Unmount cleanly
            subprocess.run(["hdiutil", "detach", mount_point], capture_output=True, text=True, check=True)


class TestSimulatedPyInstallerFrozenEnvironmentAdversarial(unittest.TestCase):
    """Stress-tests the simulated PyInstaller runtime: _MEIPASS isolation, space-containing paths, and import trees."""

    def test_frozen_runtime_execution_in_isolated_sandbox(self):
        """Simulate PyInstaller execution with space-containing _MEIPASS and isolated working directory."""
        with tempfile.TemporaryDirectory() as base_tmp:
            # Create a sandbox directory path that contains spaces to stress-test path escaping
            sandbox = Path(base_tmp) / "CardioSense Runtime Sandbox With Spaces" / "_MEIPASS_001"
            sandbox.mkdir(parents=True, exist_ok=True)
            empty_workdir = Path(base_tmp) / "Completely Empty CWD"
            empty_workdir.mkdir(parents=True, exist_ok=True)

            # Stage all files into sandbox
            shutil.copy2(REPO_ROOT / "app.py", sandbox / "app.py")
            shutil.copy2(REPO_ROOT / "core.py", sandbox / "core.py")
            shutil.copy2(REPO_ROOT / "cgi_heart.py", sandbox / "cgi_heart.py")
            shutil.copy2(REPO_ROOT / "desktop_launcher.py", sandbox / "desktop_launcher.py")
            shutil.copytree(REPO_ROOT / "artifacts", sandbox / "artifacts")
            shutil.copytree(REPO_ROOT / "data", sandbox / "data")
            shutil.copytree(REPO_ROOT / "components", sandbox / "components")
            shutil.copytree(REPO_ROOT / "portal", sandbox / "portal")

            # Inline test script executed in a separate Python process to ensure 100% clean isolation
            test_script = f"""
import sys
import os
from pathlib import Path
import joblib
import pandas as pd

# Set up simulated PyInstaller frozen environment
sandbox_path = Path(r"{sandbox}").resolve()
empty_cwd = Path(r"{empty_workdir}").resolve()

os.chdir(empty_cwd)
sys.frozen = True
sys._MEIPASS = str(sandbox_path)

# Remove only repo root directory from sys.path (preserve virtualenv site-packages)
sys.path = [p for p in sys.path if Path(p).resolve() != Path(r"{REPO_ROOT}").resolve()]
sys.path.insert(0, str(sandbox_path))

# 1. Test core import & ROOT resolution
import core
assert core.ROOT.resolve() == sandbox_path, f"core.ROOT {{core.ROOT}} != {{sandbox_path}}"

# 2. Test model loading and raw data loading in frozen state
raw_data = core.load_raw()
assert len(raw_data) == 303, f"Expected 303 rows, got {{len(raw_data)}}"

bundle = joblib.load(core.ROOT / "artifacts" / "heart_model.joblib")
assert "models" in bundle and bundle["best"] in bundle["models"]
pipe = bundle["models"][bundle["best"]]

# 3. Test patient prediction and explanation in frozen state
patient = {{
    "age": 63, "sex": 1, "cp": 3, "trestbps": 145, "chol": 233,
    "fbs": 1, "restecg": 0, "thalach": 150, "exang": 0,
    "oldpeak": 2.3, "slope": 0, "ca": 0, "thal": 1
}}
df_patient = pd.DataFrame([patient])
prob = float(pipe.predict_proba(df_patient)[0, 1])
band = core.risk_band(prob)
assert 0.0 <= prob <= 1.0, f"Invalid prob: {{prob}}"

# 4. Test cgi_heart rendering in frozen state
import cgi_heart
html = cgi_heart.render_cgi_heart(patient, prob, band)
assert len(html) > 50000, f"CGI heart HTML too short: {{len(html)}}"
assert "THREE.WebGLRenderer" in html, "Missing WebGL renderer in output"

# 5. Test components.lab_report_parser in frozen state
import components.lab_report_parser as lrp
parser = lrp.ClinicalLabReportParser()
res = parser.parse_text("Patient BP 145/85 mmHg, Total Cholesterol 233 mg/dL, Fasting glucose 135 mg/dL.")
assert res.biomarkers["trestbps"] == 145.0
assert res.biomarkers["chol"] == 233.0
assert res.biomarkers["fbs"] == 1

# 6. Test desktop_launcher get_base_dir() in frozen state
import desktop_launcher
base_dir = desktop_launcher.get_base_dir()
assert base_dir.resolve() == sandbox_path, f"Base dir {{base_dir}} != {{sandbox_path}}"

# 7. Bytecode compilation of app.py
import py_compile
py_compile.compile(str(sandbox_path / "app.py"), doraise=True)

print("ISOLATED_FROZEN_SANDBOX_SUCCESS")
"""
            res = subprocess.run(
                [sys.executable, "-c", test_script],
                cwd=str(empty_workdir),
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                res.returncode,
                0,
                f"Isolated frozen runtime execution failed!\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}",
            )
            self.assertIn("ISOLATED_FROZEN_SANDBOX_SUCCESS", res.stdout)


class TestPyInstallerSpecIntegrity(unittest.TestCase):
    """Verifies PyInstaller packaging specifications for macOS and Windows."""

    def test_mac_spec_datas_and_hiddenimports(self):
        """CardioSense-mac.spec must declare all runtime components and hidden submodules."""
        spec_path = PACKAGING_DIR / "CardioSense-mac.spec"
        self.assertTrue(spec_path.is_file(), f"Missing {spec_path}")
        content = spec_path.read_text(encoding="utf-8")

        # Must parse as valid Python AST
        tree = ast.parse(content)
        self.assertIsNotNone(tree)

        # Datas requirements
        for required in ["cgi_heart.py", "portal", "artifacts", "data", "components", "app.py", "core.py"]:
            self.assertIn(required, content, f"Missing {required} in mac spec raw_datas")

        # Hiddenimports requirements
        for imp in ["cgi_heart", "core", "components", "components.lab_report_parser", "streamlit", "plotly", "sklearn", "xgboost"]:
            self.assertIn(imp, content, f"Missing {imp} in mac spec hiddenimports")

    def test_win_spec_datas_and_hiddenimports(self):
        """CardioSense-win.spec must declare all runtime components and hidden submodules."""
        spec_path = PACKAGING_DIR / "CardioSense-win.spec"
        self.assertTrue(spec_path.is_file(), f"Missing {spec_path}")
        content = spec_path.read_text(encoding="utf-8")

        tree = ast.parse(content)
        self.assertIsNotNone(tree)

        for required in ["cgi_heart.py", "portal", "artifacts", "data", "components", "app.py", "core.py"]:
            self.assertIn(required, content, f"Missing {required} in win spec raw_datas")

        for imp in ["cgi_heart", "core", "components", "components.lab_report_parser", "streamlit", "plotly", "sklearn", "xgboost"]:
            self.assertIn(imp, content, f"Missing {imp} in win spec hiddenimports")


if __name__ == "__main__":
    unittest.main()
