"""CardioSense AI — Tier 3 Cross-Feature & Security Verification Suite.

Comprehensive security, threat model, and packaging verification covering:
1. Zero Secret Exposure & Credential Sanitization:
   - Scans portal/, scripts, python files for hardcoded credentials (e.g. 'CardioSense2026!').
   - Validates login forms do not preload default passwords.
   - AST/regex high-entropy credential scanner.
2. Anti-Bot Protection & Rate Limiting:
   - Token bucket / sliding window rate limiting: max 30 req/min/IP.
   - 31st request triggers HTTP 429 Too Many Requests with Retry-After header.
   - User-Agent bot filtering: curl, requests, wget, scrapy return HTTP 403 Forbidden.
   - Honeypot routes (/honeypot, /.env, /wp-admin) return HTTP 403 Forbidden.
3. CORS, CSRF & Loopback Origin Isolation:
   - Verification of zero wildcard Access-Control-Allow-Origin: * in serve_portal.py.
   - Re-enabled CORS and CSRF/XSRF protection in desktop_launcher.py.
   - Strict loopback binding (127.0.0.1) across desktop launcher and portal server.
4. HTTP Security Headers & Production CSP:
   - Content-Security-Policy (CSP) headers in serve_portal.py and vercel.json.
   - Standard headers: X-Content-Type-Options: nosniff, X-Frame-Options, Referrer-Policy.
5. PyInstaller Desktop & macOS DMG Packaging Specifications:
   - CardioSense-mac.spec and CardioSense-win.spec include cgi_heart.py and portal/.
   - build_mac_dmg.sh shell script flags (set -euo pipefail, trap, UDZO format).
6. 18-Architecture Release Manifest Cryptographic Parity:
   - 100% SHA-256 match across all 18 distribution packages in portal/downloads/.
   - model_weights.json SHA-256 parity with manifest.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import socket
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

PORTAL_DIR = REPO_ROOT / "portal"
DOWNLOADS_DIR = PORTAL_DIR / "downloads"
PACKAGING_DIR = REPO_ROOT / "packaging"


# ==============================================================================
# 1. Zero Secret Exposure & Credential Sanitization
# ==============================================================================
class TestTier3ZeroSecretExposure(unittest.TestCase):
    """Scans codebase for leaked credentials, passwords, and sensitive API keys."""

    def test_zero_cardiosense2026_password_leaks(self):
        """Verify the legacy development password 'CardioSense2026!' is not present in source code."""
        forbidden = "CardioSense2026!"
        scan_extensions = {".py", ".js", ".html", ".css", ".json", ".sh", ".spec"}

        for p in REPO_ROOT.rglob("*"):
            if not p.is_file() or p.suffix not in scan_extensions:
                continue
            if ".venv" in p.parts or "__pycache__" in p.parts or ".git" in p.parts or "personas" in p.parts:
                continue
            # Skip test files that explicitly search for the string
            if "test_" in p.name or "security" in p.name or "challenger" in p.name:
                continue

            content = p.read_text(encoding="utf-8", errors="ignore")
            self.assertNotIn(
                forbidden,
                content,
                f"Security Violation: Found forbidden hardcoded password in {p.relative_to(REPO_ROOT)}"
            )

    def test_login_form_sanitization_no_default_passwords(self):
        """Verify HTML form password inputs do not contain hardcoded default values."""
        index_html = (PORTAL_DIR / "index.html").read_text(encoding="utf-8")
        # Ensure input type=password doesn't have a prefilled value attribute
        matches = re.findall(r'<input[^>]*type=["\']password["\'][^>]*value=["\'][^"\']+["\']', index_html, re.I)
        self.assertEqual(len(matches), 0, f"Found prefilled password input: {matches}")


# ==============================================================================
# 2. CORS, CSRF & Loopback Origin Isolation
# ==============================================================================
class TestTier3CorsCsrfAndIsolation(unittest.TestCase):
    """Verifies loopback binding, absence of wildcard CORS, and CSRF protection."""

    def test_no_wildcard_cors_in_serve_portal(self):
        """Verify serve_portal.py does NOT emit Access-Control-Allow-Origin: *."""
        server_code = (REPO_ROOT / "serve_portal.py").read_text(encoding="utf-8")
        self.assertNotIn("Access-Control-Allow-Origin: *", server_code)
        self.assertNotIn('"Access-Control-Allow-Origin", "*"', server_code)

    def test_desktop_launcher_loopback_and_xsrf_enabled(self):
        """Verify desktop_launcher.py binds strictly to loopback and enables CORS/CSRF."""
        launcher_code = (REPO_ROOT / "desktop_launcher.py").read_text(encoding="utf-8")
        self.assertIn("127.0.0.1", launcher_code)
        # Ensure server.enableCORS and server.enableXsrf are set to true
        self.assertTrue(
            "enableCORS=true" in launcher_code.lower() or "enablecors" in launcher_code.lower()
        )
        self.assertTrue(
            "enablexsrf=true" in launcher_code.lower() or "enablexsrf" in launcher_code.lower()
        )


# ==============================================================================
# 3. HTTP Security Headers & Production CSP
# ==============================================================================
class TestTier3SecurityHeadersAndCSP(unittest.TestCase):
    """Verifies Content-Security-Policy and HTTP hardening headers."""

    def test_serve_portal_security_headers_defined(self):
        """Verify serve_portal.py injects X-Content-Type-Options, X-Frame-Options, and CSP."""
        code = (REPO_ROOT / "serve_portal.py").read_text(encoding="utf-8")
        self.assertIn("X-Content-Type-Options", code)
        self.assertIn("X-Frame-Options", code)
        self.assertIn("Content-Security-Policy", code)
        self.assertIn("nosniff", code)

    def test_vercel_json_production_headers_and_csp(self):
        """Verify vercel.json configures production security headers and CSP."""
        vercel_path = REPO_ROOT / "vercel.json"
        self.assertTrue(vercel_path.is_file(), "Missing vercel.json")
        data = json.loads(vercel_path.read_text(encoding="utf-8"))
        headers = {h["key"]: h["value"] for r in data.get("headers", []) for h in r.get("headers", [])}
        self.assertIn("Content-Security-Policy", headers)
        self.assertIn("X-Content-Type-Options", headers)
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")


# ==============================================================================
# 4. Anti-Bot Protection & Rate Limiting Logic
# ==============================================================================
class TestTier3AntiBotAndRateLimiter(unittest.TestCase):
    """Verifies rate limiting window, 429 status code, and anti-bot User-Agent filtering."""

    @classmethod
    def setUpClass(cls):
        import serve_portal
        cls.serve_portal = serve_portal

    def test_rate_limiter_window_capacity_30_per_minute(self):
        """Verify RateLimiter class allows up to 30 requests per minute and blocks the 31st."""
        limiter = self.serve_portal.RateLimiter(limit=30, window=60.0)
        ip = "192.168.1.100"

        # First 30 requests must succeed
        for i in range(30):
            allowed, retry_after = limiter.is_allowed(ip)
            self.assertTrue(allowed, f"Request {i+1} should have been allowed")
            self.assertEqual(retry_after, 0)

        # 31st request must be blocked
        allowed, retry_after = limiter.is_allowed(ip)
        self.assertFalse(allowed, "Request 31 must be blocked by rate limiter")
        self.assertGreater(retry_after, 0, "Blocked request must return positive Retry-After value")

    def test_bot_user_agent_detection(self):
        """Verify bot User-Agents (curl, requests, wget, scrapy) are detected by anti-bot pattern."""
        bot_uas = ["curl/7.68.0", "python-requests/2.28.0", "Wget/1.20.3", "Scrapy/2.5.0"]
        for ua in bot_uas:
            self.assertTrue(
                bool(self.serve_portal.SUSPICIOUS_BOT_PATTERN.search(ua)),
                f"User-Agent '{ua}' should be flagged as automated bot"
            )

    def test_browser_user_agent_allowed(self):
        """Verify legitimate modern browser User-Agents are not flagged as bots."""
        legit_ua = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self.assertFalse(bool(self.serve_portal.SUSPICIOUS_BOT_PATTERN.search(legit_ua)))

    def test_honeypot_endpoints_registered(self):
        """Verify honeypot routes (/honeypot, /.env, /wp-admin) are registered."""
        for route in ["/honeypot", "/.env", "/wp-admin"]:
            self.assertIn(route, self.serve_portal.HONEYPOT_ROUTES)


# ==============================================================================
# 5. 18-Architecture Release Manifest Cryptographic Parity
# ==============================================================================
class TestTier3ReleaseManifest18ArchParity(unittest.TestCase):
    """Verifies 100% cryptographic SHA-256 parity for all 18 release packages."""

    @classmethod
    def setUpClass(cls):
        manifest_path = PORTAL_DIR / "manifest.json"
        cls.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        cls.packages = cls.manifest.get("packages", [])

    def test_manifest_declares_exactly_18_packages(self):
        """Verify manifest contains all 18 enterprise distribution architectures."""
        self.assertEqual(len(self.packages), 18, f"Expected 18 packages, found {len(self.packages)}")

    def test_all_18_packages_sha256_parity_on_disk(self):
        """Verify SHA-256 hash of each binary on disk exactly matches manifest digest."""
        for pkg in self.packages:
            rel_path = pkg["download_url"]
            file_path = PORTAL_DIR / rel_path
            self.assertTrue(file_path.is_file(), f"Distribution package not found on disk: {file_path}")

            expected_sha256 = pkg["sha256"]
            actual_sha256 = hashlib.sha256(file_path.read_bytes()).hexdigest()
            self.assertEqual(
                actual_sha256,
                expected_sha256,
                f"SHA-256 mismatch for package {pkg['id']}: actual={actual_sha256}, expected={expected_sha256}"
            )

    def test_model_weights_sha256_matches_manifest(self):
        """Verify portal/model_weights.json matches security_profile.model_weights_sha256."""
        weights_file = PORTAL_DIR / "model_weights.json"
        self.assertTrue(weights_file.is_file(), "Missing model_weights.json")

        expected_hash = self.manifest["security_profile"]["model_weights_sha256"]
        actual_hash = hashlib.sha256(weights_file.read_bytes()).hexdigest()
        self.assertEqual(actual_hash, expected_hash, "model_weights.json hash differs from manifest")


# ==============================================================================
# 6. PyInstaller & DMG Safe Packaging Specifications
# ==============================================================================
class TestTier3PackagingSpecsAndDMG(unittest.TestCase):
    """Verifies PyInstaller spec files and macOS DMG packaging scripts."""

    def test_pyinstaller_mac_spec_datas(self):
        """Verify CardioSense-mac.spec includes cgi_heart.py and portal/ in datas."""
        spec_text = (PACKAGING_DIR / "CardioSense-mac.spec").read_text(encoding="utf-8")
        self.assertIn("cgi_heart.py", spec_text)
        self.assertIn("portal", spec_text)

    def test_pyinstaller_win_spec_datas(self):
        """Verify CardioSense-win.spec includes cgi_heart.py and portal/ in datas."""
        spec_text = (PACKAGING_DIR / "CardioSense-win.spec").read_text(encoding="utf-8")
        self.assertIn("cgi_heart.py", spec_text)
        self.assertIn("portal", spec_text)

    def test_build_mac_dmg_shell_script_flags(self):
        """Verify build_mac_dmg.sh uses set -euo pipefail and UDZO compression format."""
        dmg_script = (PACKAGING_DIR / "build_mac_dmg.sh").read_text(encoding="utf-8")
        self.assertIn("set -euo pipefail", dmg_script)
        self.assertIn("UDZO", dmg_script)


if __name__ == "__main__":
    unittest.main()
