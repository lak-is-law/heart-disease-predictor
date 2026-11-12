"""Standalone HTTP Server for the American Express-themed CardioSense Download Portal.
Usage:
    python serve_portal.py [--port 8080] [--no-browser]
"""
from __future__ import annotations

import argparse
import http.server
import mimetypes
import os
import socket
import socketserver
import sys
import webbrowser
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
PORTAL_DIR = ROOT_DIR / "portal"

# Ensure proper MIME types for downloads
mimetypes.init()
mimetypes.add_type("application/x-apple-diskimage", ".dmg")
mimetypes.add_type("application/x-msdos-program", ".exe")
mimetypes.add_type("application/json", ".json")


class PortalHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PORTAL_DIR), **kwargs)

    def end_headers(self):
        # Add CORS and Cache-Control headers for smooth local experience
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def guess_type(self, path):
        if path.endswith(".dmg"):
            return "application/x-apple-diskimage"
        if path.endswith(".exe"):
            return "application/x-msdownload"
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
    print(f"  Oracle Matrix:  macOS ARM64/x64 (.dmg) & Windows x64/ARM64 (.exe)")
    print("=" * 70)

    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    with socketserver.TCPServer(("127.0.0.1", port), PortalHTTPRequestHandler) as httpd:
        print(f"Serving portal at {url}. Press Ctrl+C to terminate.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down portal server...")
            httpd.server_close()
            sys.exit(0)


if __name__ == "__main__":
    main()
