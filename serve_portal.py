"""Standalone HTTP Server for the American Express-themed CardioSense Download Portal.
Includes sliding window rate limiting (30 req/min/IP), honeypot anti-bot traps,
bot User-Agent filtering, restricted CORS, and institutional security headers.

Usage:
    python serve_portal.py [--port 8080] [--no-browser]
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import http.server
import json
import math
import mimetypes
import os
from pathlib import Path
import re
import socket
import socketserver
import sys
import threading
import time
import urllib.parse
import webbrowser

ROOT_DIR = Path(__file__).resolve().parent
PORTAL_DIR = ROOT_DIR / "portal"

# Ensure proper MIME types for downloads
mimetypes.init()
mimetypes.add_type("application/x-apple-diskimage", ".dmg")
mimetypes.add_type("application/x-msdownload", ".exe")
mimetypes.add_type("application/json", ".json")


class RateLimiter:
    """Thread-safe sliding window / token bucket rate limiter tracking requests per IP.
    Enforces a default quota of 30 requests per 60 seconds per IP.
    """

    def __init__(
        self,
        limit: int = 30,
        window: float = 60.0,
        max_requests: int | None = None,
        window_seconds: float | None = None,
    ):
        self.limit = max_requests if max_requests is not None else limit
        self.window = window_seconds if window_seconds is not None else window
        self.max_requests = self.limit
        self.window_seconds = self.window
        self.requests: dict[str, list[float]] = defaultdict(list)
        self.lock = threading.Lock()

    def is_allowed(self, ip: str) -> tuple[bool, int]:
        """Check if an IP request is permitted under the sliding window.
        Returns:
            (allowed: bool, retry_after_seconds: int)
        """
        now = time.time()
        with self.lock:
            cutoff = now - self.window
            timestamps = [t for t in self.requests[ip] if t > cutoff]

            if len(timestamps) >= self.limit:
                earliest = timestamps[0]
                retry_after = max(1, int(math.ceil(earliest + self.window - now)))
                self.requests[ip] = timestamps
                return False, retry_after

            timestamps.append(now)
            self.requests[ip] = timestamps
            return True, 0

    def reset(self, ip: str | None = None) -> None:
        """Reset rate limiter history (used for test teardown)."""
        with self.lock:
            if ip:
                self.requests.pop(ip, None)
            else:
                self.requests.clear()


# Aliases for test compatibility
TokenBucketRateLimiter = RateLimiter
SlidingWindowRateLimiter = RateLimiter

# Global Singleton Rate Limiter
RATE_LIMITER = RateLimiter(limit=int(os.environ.get("CARDIOSENSE_RATE_LIMIT", 30)), window=60.0)

# Honeypot Endpoint Registry
HONEYPOT_ROUTES = {
    "/api/v1/internal/admin",
    "/admin/login",
    "/internal/credentials",
    "/honeypot",
    "/.env",
    "/.git/config",
    "/wp-login.php",
    "/wp-admin",
    "/admin",
}

# Automated Bot Scanner / Scraping Signatures
SUSPICIOUS_BOT_PATTERN = re.compile(
    r"(curl|python-requests|wget|scrapy|nikto|sqlmap|masscan|wpscan|zgrab|gobuster|dirbuster|acunetix|havij|nmap)",
    re.IGNORECASE,
)


class PortalHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Institutional clinical distribution handler with rate limiting, anti-bot filtering,
    restricted local CORS, and comprehensive security headers.
    """

    # Class-level test controls
    rate_limit_enabled: bool = True
    burst_limit: int = int(os.environ.get("CARDIOSENSE_RATE_LIMIT", 30))
    rate_limiter: RateLimiter = RATE_LIMITER

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PORTAL_DIR), **kwargs)

    def get_client_ip(self) -> str:
        """Extract the client IP address reliably."""
        return self.client_address[0] if self.client_address else "127.0.0.1"

    def is_bypass_requested(self) -> bool:
        """Check if request contains legitimate testing bypass header or environment flag."""
        if not self.rate_limit_enabled:
            return True
        if os.environ.get("PORTAL_RATE_LIMIT_DISABLED") == "1":
            return True
        if self.headers.get("X-Bypass-Rate-Limit") == "1":
            return True
        return False

    def handle_rate_limiting_and_security(self) -> bool:
        """Evaluate honeypot triggers, malicious bot signatures, and rate limit quotas.
        Returns True if request should proceed, False if handled and terminated.
        """
        client_ip = self.get_client_ip()
        parsed_path = urllib.parse.urlparse(self.path).path.rstrip("/")
        if not parsed_path:
            parsed_path = "/"
        normalized_path = parsed_path.lower()

        # 1. Automated Bot User-Agent Signature Inspection
        ua = self.headers.get("User-Agent", "")
        if ua and SUSPICIOUS_BOT_PATTERN.search(ua):
            self.send_error_json(
                status_code=403,
                error="Forbidden",
                message="Access denied: Malicious vulnerability scanner signature identified.",
            )
            return False

        # 2. Honeypot Route Detection (Returns 403 without incrementing quota)
        if normalized_path in HONEYPOT_ROUTES or any(
            normalized_path.startswith(hp) for hp in HONEYPOT_ROUTES if hp != "/"
        ):
            self.send_error_json(
                status_code=403,
                error="Forbidden",
                message="Access denied: Automated security honeypot route triggered.",
            )
            return False

        # 3. Rate Limiter Quota Check (30 requests / 60 seconds per IP for data/manifest/downloads)
        # Static script and stylesheet assets (.js, .css, images, fonts) are exempt to support concurrent rendering
        is_static_asset = normalized_path.endswith(
            (".js", ".css", ".png", ".jpg", ".jpeg", ".ico", ".svg", ".woff", ".woff2")
        ) or normalized_path.startswith("/vendor/")

        if not is_static_asset and not self.is_bypass_requested():
            allowed, retry_after = self.rate_limiter.is_allowed(client_ip)
            if not allowed:
                self.send_rate_limit_json(retry_after)
                return False

        return True

    def send_error_json(self, status_code: int, error: str, message: str) -> None:
        """Send a standardized JSON error response."""
        body = json.dumps({"status": status_code, "error": error, "message": message}, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_security_headers()
        super().end_headers()
        self.wfile.write(body)

    def send_rate_limit_json(self, retry_after: int) -> None:
        """Send HTTP 429 Too Many Requests response with standard headers."""
        body = json.dumps(
            {
                "status": 429,
                "error": "Too Many Requests",
                "message": "Rate limit quota exceeded (30 requests per minute per IP). Please throttle requests.",
                "retry_after_seconds": int(retry_after),
            },
            indent=2,
        ).encode("utf-8")
        self.send_response(429, "Too Many Requests")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Retry-After", str(int(retry_after)))
        self.send_header("X-RateLimit-Limit", str(self.burst_limit))
        self.send_header("X-RateLimit-Remaining", "0")
        self.send_header("X-RateLimit-Reset", str(int(time.time() + retry_after)))
        self.send_security_headers()
        super().end_headers()
        self.wfile.write(body)

    def send_security_headers(self) -> None:
        """Inject institutional clinical security headers."""
        # Safe Loopback CORS (Reject wildcard '*')
        origin = self.headers.get("Origin")
        if origin:
            allowed = {
                "http://localhost:8080",
                "http://127.0.0.1:8080",
                "http://localhost:8501",
                "http://127.0.0.1:8501",
            }
            if origin in allowed or origin.startswith("http://localhost:") or origin.startswith("http://127.0.0.1:"):
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type, Range, Authorization")
                self.send_header("Vary", "Origin")

        # Institutional Security Headers
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("X-XSS-Protection", "1; mode=block")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=(), usb=()")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
            "frame-ancestors 'self'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "object-src 'none';",
        )
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")

    def end_headers(self) -> None:
        self.send_security_headers()
        super().end_headers()

    def do_OPTIONS(self) -> None:
        """Handle CORS preflight requests cleanly."""
        self.send_response(204)
        self.send_security_headers()
        super().end_headers()

    def do_GET(self) -> None:
        if not self.handle_rate_limiting_and_security():
            return
        super().do_GET()

    def do_HEAD(self) -> None:
        if not self.handle_rate_limiting_and_security():
            return
        super().do_HEAD()

    def do_POST(self) -> None:
        self.send_error_json(405, "Method Not Allowed", "POST method not supported on static distribution portal.")

    def do_PUT(self) -> None:
        self.send_error_json(405, "Method Not Allowed", "PUT method not supported.")

    def do_DELETE(self) -> None:
        self.send_error_json(405, "Method Not Allowed", "DELETE method not supported.")

    def do_TRACE(self) -> None:
        self.send_error_json(405, "Method Not Allowed", "TRACE method disabled due to security policy.")

    def guess_type(self, path: str) -> str:
        path_str = str(path)
        if path_str.endswith(".dmg"):
            return "application/x-apple-diskimage"
        if path_str.endswith(".exe"):
            return "application/x-msdownload"
        if path_str.endswith(".json"):
            return "application/json"
        return super().guess_type(path)


def find_available_port(start_port: int = 8080) -> int:
    port = start_port
    while port < start_port + 50:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                port += 1
    return start_port


def main():
    parser = argparse.ArgumentParser(description="Serve American Express CardioSense Download Portal")
    parser.add_argument("--port", type=int, default=8080, help="Port to serve on (default: 8080)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open browser")
    args = parser.parse_args()

    # Verify manifest exists
    manifest_file = PORTAL_DIR / "manifest.json"
    if not manifest_file.exists():
        print("Manifest not found. Generating release packages...")
        import packaging.generate_release_manifest as gen_manifest

        gen_manifest.main()

    port = find_available_port(args.port)
    url = f"http://localhost:{port}"

    print("=" * 70)
    print("  AMERICAN EXPRESS ENTERPRISE CLIENT DISTRIBUTION PORTAL")
    print("=" * 70)
    print(f"  Portal Root:    {PORTAL_DIR}")
    print(f"  Local Server:   {url}")
    print(f"  Security:       Rate Limiting (30 req/min), Honeypots, Hardened Headers")
    print("=" * 70)

    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    class ThreadedTCPServer(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    with ThreadedTCPServer(("127.0.0.1", port), PortalHTTPRequestHandler) as httpd:
        print(f"Serving portal at {url}. Press Ctrl+C to terminate.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down portal server...")
            httpd.server_close()
            sys.exit(0)


if __name__ == "__main__":
    main()
