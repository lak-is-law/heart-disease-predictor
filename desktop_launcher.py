#!/usr/bin/env python3
"""CardioSense Desktop Application Launcher
Provides a native desktop wrapper for the Streamlit heart disease predictor.
Compatible with:
- macOS Apple Silicon (ARM64)
- macOS Intel (x86_64)
- Windows 10/11 64-bit (x64)
- Windows ARM64
"""
from __future__ import annotations

import argparse
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

# --- PyInstaller Internal CLI Dispatcher (Fixes Subprocess Fork-Bomb) ---
if len(sys.argv) > 1 and sys.argv[1] == "--streamlit-internal":
    from streamlit.web import cli as stcli

    sys.argv = ["streamlit"] + sys.argv[2:]
    sys.exit(stcli.main())


def get_base_dir() -> Path:
    """Return the base directory whether running from source or frozen binary."""
    if getattr(sys, "frozen", False):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass and Path(meipass).exists():
            return Path(meipass).resolve()
        return Path(sys.executable).resolve().parent

    # Check macOS .app bundle Resources layout
    launcher_path = Path(__file__).resolve()
    bundle_resources = launcher_path.parent.parent / "Resources"
    if (bundle_resources / "app.py").exists():
        return bundle_resources.resolve()

    return launcher_path.parent


def find_free_port(preferred: int = 8501) -> int:
    """Attempt to bind to the preferred port, otherwise find an available dynamic port."""
    for port in (preferred, 8502, 8503, 8504, 8505):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    # Fallback to random free port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_for_server(url: str, timeout: float = 25.0) -> bool:
    """Poll the Streamlit health endpoint until responsive."""
    health_url = f"{url}/_stcore/health"
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(health_url, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.3)
    return False


def run_desktop() -> None:
    parser = argparse.ArgumentParser(description="CardioSense Enterprise Desktop Application")
    parser.add_argument("--port", type=int, default=None, help="Force specific port")
    parser.add_argument("--browser-only", action="store_true", help="Launch directly in browser without native webview")
    args = parser.parse_args()

    base_dir = get_base_dir()
    app_script = base_dir / "app.py"
    if not app_script.exists():
        # Fallback search
        candidate = base_dir / "heart-disease-predictor" / "app.py"
        if candidate.exists():
            app_script = candidate

    port = args.port or find_free_port(8501)
    server_url = f"http://127.0.0.1:{port}"

    # Setup environment variables for clean Streamlit background operation with strict security
    env = os.environ.copy()
    env["STREAMLIT_SERVER_PORT"] = str(port)
    env["STREAMLIT_SERVER_ADDRESS"] = "127.0.0.1"
    env["STREAMLIT_BROWSER_SERVER_ADDRESS"] = "127.0.0.1"
    env["STREAMLIT_SERVER_HEADLESS"] = "true"
    env["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    env["STREAMLIT_THEME_BASE"] = "dark"
    env["STREAMLIT_SERVER_ENABLE_CORS"] = "true"
    env["STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION"] = "true"
    env["PYTHONPATH"] = f"{base_dir}:{env.get('PYTHONPATH', '')}"

    print("=" * 60)
    print("  CARDIOSENSE ENTERPRISE DESKTOP")
    print(f"  Platform: {sys.platform} ({os.uname().machine if hasattr(os, 'uname') else 'win'})")
    print(f"  Base directory: {base_dir}")
    print(f"  Internal server: {server_url} (CORS & XSRF Enforced)")
    print("=" * 60)

    # Spawn Streamlit process with hardened CORS and XSRF protection
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_script),
        "--server.headless",
        "true",
        "--server.port",
        str(port),
        "--server.address",
        "127.0.0.1",
        "--browser.serverAddress",
        "127.0.0.1",
        "--server.enableCORS=true",
        "--server.enableXsrfProtection=true",
    ]
    if getattr(sys, "frozen", False):
        cmd = [
            sys.executable,
            "--streamlit-internal",
            "run",
            str(app_script),
            "--server.headless",
            "true",
            "--server.port",
            str(port),
            "--server.address",
            "127.0.0.1",
            "--browser.serverAddress",
            "127.0.0.1",
            "--server.enableCORS=true",
            "--server.enableXsrfProtection=true",
        ]

    proc = subprocess.Popen(
        cmd,
        cwd=str(base_dir),
        env=env,
        stdout=subprocess.DEVNULL if getattr(sys, "frozen", False) else None,
        stderr=subprocess.DEVNULL if getattr(sys, "frozen", False) else None,
    )

    def shutdown(sig=None, frame=None):
        print("\nShutting down CardioSense Enterprise...")
        try:
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=3)
        except Exception:
            proc.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    print("Waiting for local server initialization...")
    if not wait_for_server(server_url):
        print("Error: CardioSense local backend server failed to initialize in time.")
        shutdown()
        return

    print("Server ready! Initializing user interface...")

    # Attempt to use pywebview for native desktop window experience
    use_webview = False
    if not args.browser_only:
        try:
            import webview  # type: ignore

            use_webview = True
            print("Launching native desktop window frame (PyWebView)...")
            window = webview.create_window(
                title="CardioSense Enterprise - Heart Disease Prediction",
                url=server_url,
                width=1280,
                height=850,
                min_size=(960, 650),
                confirm_close=False,
            )
            webview.start()
            shutdown()
            return
        except ImportError:
            use_webview = False

    if not use_webview:
        print("Launching desktop client in default browser...")
        webbrowser.open(server_url)
        print("CardioSense is running. Press Ctrl+C to stop.")
        try:
            proc.wait()
        except KeyboardInterrupt:
            shutdown()


if __name__ == "__main__":
    run_desktop()
