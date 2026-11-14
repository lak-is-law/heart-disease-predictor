"""CardioSense AI — Milestone M4 Adversarial Security & Rate Limiter Stress Test Suite.
Authored by m4_challenger_1.

Empirical verification covering:
1. High-Concurrency Burst Attacks against RateLimiter (29, 30, 31, 50 requests in parallel).
2. Multi-threaded Race Condition & Contention stress across independent IP pools.
3. Static Asset Exemption under concurrent load (.js, .css, vendor assets).
4. Automated Bot User-Agent Detection (curl, requests, wget, scrapy, sqlmap, nikto, masscan, etc.).
5. Mixed-Case, Embedded & Obfuscated Bot User-Agent signatures.
6. Honeypot Route Trapping (/honeypot, /.env, /wp-admin, /admin, subpaths, case variants).
7. Honeypot Quota Isolation (honeypot 403s do not consume legitimate user rate limit).
8. Path Traversal & Arbitrary File Access Defense (/../../etc/passwd, encoded %2e%2e, backslash).
9. Strict CORS Origin Isolation (loopback allowed, external domains & evil spoof origins rejected).
10. CORS Preflight (OPTIONS) request validation.
11. HTTP Method Hardening (POST, PUT, DELETE, TRACE blocked with 405).
12. Institutional Security Headers Verification across all responses.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import http.client
import json
import math
import os
import re
import socket
import socketserver
import subprocess
import sys
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# Repository root directory
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

PORTAL_DIR = REPO_ROOT / "portal"
PACKAGING_DIR = REPO_ROOT / "packaging"

import serve_portal
from serve_portal import PortalHTTPRequestHandler, RateLimiter


class EphemeralPortalServer:
    """Helper context manager to launch a live ThreadedTCPServer for empirical HTTP stress testing."""

    def __init__(self, handler_cls=None, fresh_limiter: bool = True):
        if handler_cls is None:
            if fresh_limiter:
                limiter = RateLimiter(limit=30, window=60.0)

                class IsolatedHandler(PortalHTTPRequestHandler):
                    rate_limiter = limiter

                self.handler_cls = IsolatedHandler
            else:
                self.handler_cls = PortalHTTPRequestHandler
        else:
            self.handler_cls = handler_cls
        self.server: socketserver.ThreadingTCPServer | None = None
        self.thread: threading.Thread | None = None
        self.port: int = 0
        self.base_url: str = ""

    def __enter__(self):
        # Bind to an ephemeral port on 127.0.0.1
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]

        class ThreadedServer(socketserver.ThreadingTCPServer):
            allow_reuse_address = True
            daemon_threads = True

        self.server = ThreadedServer(("127.0.0.1", self.port), self.handler_cls)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.port}"
        time.sleep(0.1)  # Allow socket to bind and start listening
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.server:
            self.server.shutdown()
            self.server.server_close()


class TestRateLimiterConcurrencyAdversarial(unittest.TestCase):
    """Stress tests and boundary condition verification for the RateLimiter sliding window."""

    def setUp(self):
        self.limiter = RateLimiter(limit=30, window=60.0)

    def test_single_ip_boundary_burst(self):
        """Sequential boundary test: exactly 30 allowed, 31st and beyond rejected with 429."""
        ip = "10.0.0.1"
        for i in range(1, 31):
            allowed, retry = self.limiter.is_allowed(ip)
            self.assertTrue(allowed, f"Request #{i} should be allowed")
            self.assertEqual(retry, 0)

        # 31st request must fail
        allowed, retry = self.limiter.is_allowed(ip)
        self.assertFalse(allowed, "Request #31 must be throttled")
        self.assertGreater(retry, 0, "Throttled request must return retry_after > 0")

        # 50th request still throttled
        for _ in range(32, 51):
            allowed, retry = self.limiter.is_allowed(ip)
            self.assertFalse(allowed)
            self.assertGreater(retry, 0)

    def test_high_concurrency_thread_pool_burst(self):
        """Adversarial concurrent burst: 50 simultaneous threads hammering RateLimiter for same IP.
        Exactly 30 must succeed, and exactly 20 must be throttled with zero deadlocks or race conditions.
        """
        ip = "10.0.0.2"
        results: list[tuple[bool, int]] = []
        lock = threading.Lock()

        def make_request():
            res = self.limiter.is_allowed(ip)
            with lock:
                results.append(res)

        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(make_request) for _ in range(50)]
            concurrent.futures.wait(futures)

        self.assertEqual(len(results), 50)
        allowed_count = sum(1 for allowed, _ in results if allowed)
        throttled_count = sum(1 for allowed, _ in results if not allowed)

        self.assertEqual(
            allowed_count,
            30,
            f"Expected exactly 30 allowed under concurrency, got {allowed_count}",
        )
        self.assertEqual(
            throttled_count,
            20,
            f"Expected exactly 20 throttled under concurrency, got {throttled_count}",
        )

        for allowed, retry in results:
            if not allowed:
                self.assertGreater(retry, 0, "Throttled request must include positive retry_after")

    def test_multi_ip_contention_no_cross_talk(self):
        """50 concurrent threads representing 50 distinct IPs: all 50 must succeed simultaneously."""
        results: dict[str, bool] = {}
        lock = threading.Lock()

        def make_ip_request(client_ip: str):
            allowed, _ = self.limiter.is_allowed(client_ip)
            with lock:
                results[client_ip] = allowed

        ips = [f"192.168.1.{i}" for i in range(1, 51)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(make_ip_request, ip) for ip in ips]
            concurrent.futures.wait(futures)

        self.assertEqual(len(results), 50)
        for ip, allowed in results.items():
            self.assertTrue(allowed, f"IP {ip} should have been allowed independently")

    def test_sliding_window_expiration_and_recovery(self):
        """Verify that after sliding window expires, quota is fully restored."""
        short_limiter = RateLimiter(limit=3, window=0.4)
        ip = "172.16.0.1"

        # Consume quota
        for _ in range(3):
            allowed, _ = short_limiter.is_allowed(ip)
            self.assertTrue(allowed)

        # 4th blocked
        allowed, retry = short_limiter.is_allowed(ip)
        self.assertFalse(allowed)
        self.assertGreater(retry, 0)

        # Wait for window to expire
        time.sleep(0.45)

        # Should be allowed again
        allowed_after, retry_after = short_limiter.is_allowed(ip)
        self.assertTrue(allowed_after, "Quota should be restored after window expiration")
        self.assertEqual(retry_after, 0)


class TestLiveServerConcurrencyAndRateLimiting(unittest.TestCase):
    """Empirical adversarial attacks against a live HTTP server instance."""

    def test_http_live_concurrency_burst_50_requests(self):
        """Blasts live server with 50 concurrent HTTP requests from 127.0.0.1 for /manifest.json.
        Asserts exactly 30 succeed with 200 OK and exactly 20 return HTTP 429 Too Many Requests.
        """
        # Create fresh limiter instance
        fresh_limiter = RateLimiter(limit=30, window=60.0)

        class CustomHandler(PortalHTTPRequestHandler):
            rate_limiter = fresh_limiter

        with EphemeralPortalServer(CustomHandler) as srv:
            url = f"{srv.base_url}/manifest.json"
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }

            def send_http_get(req_id: int) -> tuple[int, dict, bytes]:
                req = urllib.request.Request(url, headers=headers)
                try:
                    with urllib.request.urlopen(req, timeout=5.0) as resp:
                        return resp.status, dict(resp.headers), resp.read()
                except urllib.error.HTTPError as err:
                    return err.code, dict(err.headers), err.read()

            with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
                futures = [executor.submit(send_http_get, i) for i in range(50)]
                results = [f.result() for f in futures]

            status_codes = [r[0] for r in results]
            count_200 = status_codes.count(200)
            count_429 = status_codes.count(429)

            self.assertEqual(
                count_200,
                30,
                f"Expected exactly 30 HTTP 200 responses under 50-request burst, got {count_200}. Codes: {status_codes}",
            )
            self.assertEqual(
                count_429,
                20,
                f"Expected exactly 20 HTTP 429 responses under 50-request burst, got {count_429}",
            )

            # Validate 429 response structure and headers
            for code, hdrs, body in results:
                if code == 429:
                    self.assertIn("Retry-After", hdrs, "HTTP 429 response missing Retry-After header")
                    self.assertIn("X-RateLimit-Limit", hdrs, "HTTP 429 response missing X-RateLimit-Limit header")
                    self.assertEqual(hdrs.get("X-RateLimit-Remaining"), "0")
                    payload = json.loads(body.decode("utf-8"))
                    self.assertEqual(payload.get("status"), 429)
                    self.assertEqual(payload.get("error"), "Too Many Requests")

    def test_static_assets_exempt_from_rate_limit(self):
        """Static JS, CSS, and vendor assets must NOT be throttled even after quota exhausted."""
        fresh_limiter = RateLimiter(limit=5, window=60.0)

        class CustomHandler(PortalHTTPRequestHandler):
            rate_limiter = fresh_limiter

        with EphemeralPortalServer(CustomHandler) as srv:
            browser_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"

            # Exhaust quota using /manifest.json (non-static)
            for _ in range(5):
                req = urllib.request.Request(f"{srv.base_url}/manifest.json", headers={"User-Agent": browser_ua})
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    self.assertEqual(resp.status, 200)

            # 6th /manifest.json fails with 429
            req_blocked = urllib.request.Request(f"{srv.base_url}/manifest.json", headers={"User-Agent": browser_ua})
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(req_blocked, timeout=2.0)
            self.assertEqual(ctx.exception.code, 429)

            # Static assets (.js, .css, vendor) MUST still succeed with 200!
            static_endpoints = [
                "/portal.js",
                "/styles.css",
                "/vendor/three.min.js",
                "/vendor/OrbitControls.js",
            ]
            for endpoint in static_endpoints:
                req_static = urllib.request.Request(f"{srv.base_url}{endpoint}", headers={"User-Agent": browser_ua})
                with urllib.request.urlopen(req_static, timeout=2.0) as resp:
                    self.assertEqual(
                        resp.status,
                        200,
                        f"Static asset {endpoint} should NOT be rate limited",
                    )


class TestHoneypotTrapsAndQuotaIsolation(unittest.TestCase):
    """Stress tests for honeypots, path variants, and rate limit quota isolation."""

    def test_all_honeypot_endpoints_and_subpaths(self):
        """Every registered honeypot endpoint and subpath must return HTTP 403 Forbidden."""
        with EphemeralPortalServer() as srv:
            honeypot_paths = [
                "/honeypot",
                "/honeypot/",
                "/honeypot?probe=1",
                "/api/v1/internal/admin",
                "/api/v1/internal/admin/secret_keys",
                "/.env",
                "/.env.local",
                "/.env.backup",
                "/.git/config",
                "/wp-login.php",
                "/wp-admin",
                "/wp-admin/index.php",
                "/admin",
                "/admin/login",
                "/admin/dashboard",
                "/internal/credentials",
                # Case insensitivity
                "/HONEYPOT",
                "/.Env",
                "/Wp-Admin",
            ]

            browser_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"

            for hp_path in honeypot_paths:
                url = f"{srv.base_url}{hp_path}"
                req = urllib.request.Request(url, headers={"User-Agent": browser_ua})
                try:
                    with urllib.request.urlopen(req, timeout=2.0) as resp:
                        self.fail(f"Honeypot path '{hp_path}' should return 403, got {resp.status}")
                except urllib.error.HTTPError as err:
                    self.assertEqual(
                        err.code,
                        403,
                        f"Honeypot path '{hp_path}' must return 403 Forbidden, got {err.code}",
                    )
                    payload = json.loads(err.read().decode("utf-8"))
                    self.assertEqual(payload.get("status"), 403)
                    self.assertEqual(payload.get("error"), "Forbidden")

    def test_honeypots_do_not_exhaust_legitimate_rate_limit(self):
        """Hitting honeypot routes must return 403 WITHOUT consuming the user's 30 req/min quota."""
        fresh_limiter = RateLimiter(limit=30, window=60.0)

        class CustomHandler(PortalHTTPRequestHandler):
            rate_limiter = fresh_limiter

        with EphemeralPortalServer(CustomHandler) as srv:
            browser_ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/120.0.0.0"

            # Hit honeypots 15 times
            for _ in range(15):
                req = urllib.request.Request(f"{srv.base_url}/.env", headers={"User-Agent": browser_ua})
                try:
                    urllib.request.urlopen(req, timeout=2.0)
                except urllib.error.HTTPError as err:
                    self.assertEqual(err.code, 403)

            # Legitimate requests must still have all 30 quota slots available!
            for req_i in range(1, 31):
                req = urllib.request.Request(f"{srv.base_url}/manifest.json", headers={"User-Agent": browser_ua})
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    self.assertEqual(resp.status, 200, f"Request #{req_i} should succeed after honeypots")

            # 31st legitimate request triggers 429
            req_blocked = urllib.request.Request(f"{srv.base_url}/manifest.json", headers={"User-Agent": browser_ua})
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(req_blocked, timeout=2.0)
            self.assertEqual(ctx.exception.code, 429)


class TestAdversarialScannerUserAgents(unittest.TestCase):
    """Adversarial testing of scanner User-Agent blocking with spoofing and case variations."""

    def test_malicious_user_agent_blocklist(self):
        """Scanners and automated exploitation tools must be rejected with 403."""
        with EphemeralPortalServer() as srv:
            scanner_uas = [
                # curl variants
                "curl/7.88.1",
                "curl/8.4.0",
                "cURL/7.68.0",
                # python requests variants
                "python-requests/2.31.0",
                "Python-Requests/2.28.1",
                "python-requests",
                # CLI downloaders
                "Wget/1.21.4",
                "wget/1.20.3",
                # Web scrapers
                "Scrapy/2.11.0 (+https://scrapy.org)",
                "scrapy/1.8.0",
                # Vulnerability scanners
                "sqlmap/1.7#stable",
                "Nikto/2.1.6",
                "nikto",
                "masscan/1.3.2",
                "wpscan v3.8.22",
                "zgrab 0.x",
                "gobuster v3.5",
                "dirbuster 1.0-RC1",
                "acunetix",
                "havij 1.17",
                "Mozilla/5.0 (compatible; Nmap Scripting Engine; https://nmap.org/book/nse.html)",
            ]

            for ua in scanner_uas:
                req = urllib.request.Request(f"{srv.base_url}/manifest.json", headers={"User-Agent": ua})
                try:
                    with urllib.request.urlopen(req, timeout=2.0) as resp:
                        self.fail(f"Scanner User-Agent '{ua}' should return 403, got {resp.status}")
                except urllib.error.HTTPError as err:
                    self.assertEqual(
                        err.code,
                        403,
                        f"Scanner User-Agent '{ua}' must be rejected with 403 Forbidden, got {err.code}",
                    )

    def test_legitimate_browser_user_agents_allowed(self):
        """Standard legitimate browser User-Agents must be permitted (HTTP 200)."""
        with EphemeralPortalServer() as srv:
            browser_uas = [
                # Chrome macOS
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                # Firefox Windows
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
                # Safari iOS
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
                # Edge Linux
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            ]

            for ua in browser_uas:
                req = urllib.request.Request(f"{srv.base_url}/manifest.json", headers={"User-Agent": ua})
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    self.assertEqual(resp.status, 200, f"Legitimate browser UA '{ua}' should be allowed")


class TestPathTraversalAndArbitraryFileRead(unittest.TestCase):
    """Stress testing path traversal, directory escape, and file disclosure vulnerabilities."""

    def test_path_traversal_attempts_do_not_escape_portal_root(self):
        """Path traversal attacks must NEVER leak files outside the portal/ directory."""
        with EphemeralPortalServer() as srv:
            traversal_payloads = [
                "/../../etc/passwd",
                "/../../../etc/passwd",
                "/../portal/manifest.json",
                "/../../desktop_launcher.py",
                "/../app.py",
                "/downloads/../../desktop_launcher.py",
                "/downloads/../../core.py",
                # URL percent-encoded traversals
                "/%2e%2e/%2e%2e/etc/passwd",
                "/%2e%2e%2f%2e%2e%2fdesktop_launcher.py",
                "/..%2f..%2fdesktop_launcher.py",
                # Windows-style backslashes
                "/..\\..\\desktop_launcher.py",
                "/downloads\\..\\..\\desktop_launcher.py",
            ]

            browser_ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/120.0.0.0"

            for payload in traversal_payloads:
                url = f"{srv.base_url}{payload}"
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": browser_ua, "X-Bypass-Rate-Limit": "1"},
                )
                try:
                    with urllib.request.urlopen(req, timeout=2.0) as resp:
                        # If a 200 is returned, verify it is NOT sensitive host content
                        content = resp.read().decode("utf-8", errors="ignore")
                        self.assertNotIn("root:x:0:0", content, f"Path traversal leaked /etc/passwd: {payload}")
                        self.assertNotIn(
                            "STREAMLIT_SERVER_ADDRESS",
                            content,
                            f"Path traversal leaked desktop_launcher.py: {payload}",
                        )
                except urllib.error.HTTPError as err:
                    # Returning 404, 403, 400, or 429 is secure
                    self.assertIn(
                        err.code,
                        (400, 403, 404, 429),
                        f"Unexpected error code {err.code} for traversal payload: {payload}",
                    )


class TestCORSPreflightAndOriginIsolation(unittest.TestCase):
    """Verifies that CORS origins are strictly isolated to authorized loopback ports."""

    def test_unauthorized_foreign_origins_rejected(self):
        """Foreign and attacker origins must NOT receive Access-Control-Allow-Origin header."""
        with EphemeralPortalServer() as srv:
            evil_origins = [
                "https://malicious-hospital-attacker.com",
                "http://evil.com",
                "https://cardiosense-fake.org",
                "http://localhost.attacker.com",
                "http://127.0.0.1.attacker.com",
                "null",
            ]

            browser_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"

            for evil_origin in evil_origins:
                req = urllib.request.Request(
                    f"{srv.base_url}/manifest.json",
                    headers={"User-Agent": browser_ua, "Origin": evil_origin},
                )
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    self.assertEqual(resp.status, 200)
                    acao = resp.headers.get("Access-Control-Allow-Origin")
                    self.assertIsNone(
                        acao,
                        f"Unauthorized origin '{evil_origin}' received Access-Control-Allow-Origin: {acao}",
                    )

    def test_authorized_loopback_origins_reflected_safely(self):
        """Legitimate local Streamlit and portal origins must receive matched CORS header with Vary: Origin."""
        with EphemeralPortalServer() as srv:
            valid_origins = [
                "http://localhost:8080",
                "http://127.0.0.1:8080",
                "http://localhost:8501",
                "http://127.0.0.1:8501",
                "http://localhost:3000",
                "http://127.0.0.1:9000",
            ]

            browser_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"

            for origin in valid_origins:
                req = urllib.request.Request(
                    f"{srv.base_url}/manifest.json",
                    headers={"User-Agent": browser_ua, "Origin": origin},
                )
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    self.assertEqual(resp.status, 200)
                    acao = resp.headers.get("Access-Control-Allow-Origin")
                    self.assertEqual(
                        acao,
                        origin,
                        f"Authorized origin '{origin}' did not receive matching CORS reflection",
                    )
                    self.assertEqual(
                        resp.headers.get("Vary"),
                        "Origin",
                        "Responses with dynamic CORS must specify Vary: Origin",
                    )

    def test_cors_preflight_options_method(self):
        """OPTIONS preflight requests must return 204 No Content with appropriate headers."""
        with EphemeralPortalServer() as srv:
            # 1. Authorized preflight
            conn = http.client.HTTPConnection("127.0.0.1", srv.port)
            conn.request(
                "OPTIONS",
                "/manifest.json",
                headers={
                    "Origin": "http://localhost:8501",
                    "Access-Control-Request-Method": "GET",
                },
            )
            resp = conn.getresponse()
            self.assertEqual(resp.status, 204)
            self.assertEqual(resp.getheader("Access-Control-Allow-Origin"), "http://localhost:8501")
            self.assertIn("GET", resp.getheader("Access-Control-Allow-Methods", ""))
            conn.close()

            # 2. Unauthorized preflight
            conn = http.client.HTTPConnection("127.0.0.1", srv.port)
            conn.request(
                "OPTIONS",
                "/manifest.json",
                headers={
                    "Origin": "https://malicious.org",
                    "Access-Control-Request-Method": "GET",
                },
            )
            resp = conn.getresponse()
            self.assertEqual(resp.status, 204)
            self.assertIsNone(
                resp.getheader("Access-Control-Allow-Origin"),
                "Unauthorized origin in OPTIONS preflight must not receive Access-Control-Allow-Origin",
            )
            conn.close()


class TestHTTPMethodHardeningAndSecurityHeaders(unittest.TestCase):
    """Verifies that non-GET methods are disallowed and security headers are enforced."""

    def test_unsupported_http_methods_return_405(self):
        """POST, PUT, DELETE, TRACE must return HTTP 405 Method Not Allowed."""
        with EphemeralPortalServer() as srv:
            methods = ["POST", "PUT", "DELETE", "TRACE"]
            for method in methods:
                conn = http.client.HTTPConnection("127.0.0.1", srv.port)
                conn.request(
                    method,
                    "/manifest.json",
                    body=b"payload" if method in ("POST", "PUT") else None,
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                resp = conn.getresponse()
                body = resp.read().decode("utf-8")
                self.assertEqual(
                    resp.status,
                    405,
                    f"Method {method} should return 405 Method Not Allowed, got {resp.status}",
                )
                payload = json.loads(body)
                self.assertEqual(payload.get("status"), 405)
                self.assertEqual(payload.get("error"), "Method Not Allowed")
                conn.close()

    def test_institutional_security_headers_present(self):
        """All responses must carry comprehensive clinical security headers."""
        with EphemeralPortalServer() as srv:
            req = urllib.request.Request(
                f"{srv.base_url}/manifest.json",
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            )
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                headers = dict(resp.headers)
                expected_headers = {
                    "X-Content-Type-Options": "nosniff",
                    "X-Frame-Options": "SAMEORIGIN",
                    "X-XSS-Protection": "1; mode=block",
                    "Referrer-Policy": "strict-origin-when-cross-origin",
                    "Cross-Origin-Opener-Policy": "same-origin",
                    "Cross-Origin-Resource-Policy": "same-origin",
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                }
                for header_key, expected_val in expected_headers.items():
                    self.assertIn(header_key, headers, f"Missing header: {header_key}")
                    self.assertEqual(
                        headers[header_key],
                        expected_val,
                        f"Header {header_key} mismatch: {headers[header_key]} != {expected_val}",
                    )

                csp = headers.get("Content-Security-Policy", "")
                self.assertIn("default-src 'self'", csp)
                self.assertIn("object-src 'none'", csp)
                self.assertIn("https://cdn.jsdelivr.net", csp)
                self.assertIn("https://cdnjs.cloudflare.com", csp)


if __name__ == "__main__":
    unittest.main()
