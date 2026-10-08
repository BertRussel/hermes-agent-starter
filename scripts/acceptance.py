#!/usr/bin/env python3
"""Canonical local acceptance for the privacy-clean recipient handoff."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import sys

from full_system_package import accept_full_system

def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--bundle-source", required=True); p.add_argument("--output-dir", required=True); p.add_argument("--fixture-root", required=True); a = p.parse_args()
    if subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider"]).returncode:
        return 1
    try:
        receipt = accept_full_system(Path(a.bundle_source), Path(a.output_dir), Path(a.fixture_root))
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(json.dumps({"acceptance": "failed", "error": str(error)}, sort_keys=True))
        return 1
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt["acceptance"] == "passed" else 1
if __name__ == "__main__": raise SystemExit(main())
