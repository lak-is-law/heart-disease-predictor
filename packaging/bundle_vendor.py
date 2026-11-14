#!/usr/bin/env python3
"""Offline Vendor Asset Bundler for CardioSense AI Platform.

Downloads and cryptographically verifies Three.js r128 and OrbitControls r128
into portal/vendor/ for air-gapped clinical deployments.
"""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

VENDOR_MANIFEST = {
    "three.min.js": {
        "url": "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js",
        "expected_sha256": "9274bbcec8d96168626c732b5d31c775aa8cfb7eaa0599bec0c175908a2c1ce2",
        "expected_bytes": 603445,
    },
    "OrbitControls.js": {
        "url": "https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js",
        "expected_sha256": "02bb4ade710f3e607329e37a21f098bc3ac70eb6e33daf8a65e79f4db785e7b2",
        "expected_bytes": 26375,
    },
}


def stage_vendor_assets(target_dir: Path) -> bool:
    target_dir.mkdir(parents=True, exist_ok=True)
    all_ok = True

    print(f"Staging vendor assets into: {target_dir}")
    for filename, meta in VENDOR_MANIFEST.items():
        out_path = target_dir / filename
        print(f"Fetching {filename} from {meta['url']}...")
        try:
            req = urllib.request.Request(
                meta["url"],
                headers={"User-Agent": "CardioSense-Asset-Bundler/1.0"},
            )
            with urllib.request.urlopen(req) as resp:
                data = resp.read()

            actual_sha256 = hashlib.sha256(data).hexdigest()
            actual_bytes = len(data)

            if actual_sha256 != meta["expected_sha256"]:
                print(
                    f"  [ERROR] SHA-256 mismatch for {filename}!\n"
                    f"    Expected: {meta['expected_sha256']}\n"
                    f"    Actual:   {actual_sha256}",
                    file=sys.stderr,
                )
                all_ok = False
                continue

            out_path.write_bytes(data)
            print(
                f"  [OK] {filename} saved ({actual_bytes:,} bytes, "
                f"SHA-256: {actual_sha256[:16]}...)"
            )
        except Exception as exc:
            print(f"  [ERROR] Failed to download {filename}: {exc}", file=sys.stderr)
            all_ok = False

    return all_ok


if __name__ == "__main__":
    default_dir = (
        Path(__file__).resolve().parent.parent
        / "portal"
        / "vendor"
    )
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else default_dir
    success = stage_vendor_assets(dest)
    sys.exit(0 if success else 1)
