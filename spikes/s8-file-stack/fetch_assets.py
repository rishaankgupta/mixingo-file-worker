#!/usr/bin/env python3
"""Downloads the pinned fonts and Tesseract models in assets.json and checks their SHA-256.

Files already present with the right hash are kept. Set ASSETS_DIR to use another folder, and
SKIP_TESSDATA=1 to fetch the fonts only (part A needs no Tesseract models).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = Path(os.environ.get("ASSETS_DIR", HERE / "assets"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(url: str, target: Path, expected: str) -> str:
    if target.exists() and sha256(target) == expected:
        return "cached"
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + ".part")
    with urllib.request.urlopen(url, timeout=120) as response, partial.open("wb") as handle:
        while chunk := response.read(1 << 20):
            handle.write(chunk)
    actual = sha256(partial)
    if actual != expected:
        partial.unlink()
        raise SystemExit(f"{target.name}: SHA-256 mismatch (expected {expected}, got {actual})")
    partial.replace(target)
    return "downloaded"


def main() -> None:
    spec = json.loads((HERE / "assets.json").read_text(encoding="utf-8"))
    groups = ["fonts"] if os.environ.get("SKIP_TESSDATA") == "1" else ["fonts", "tessdata_best"]
    for group in groups:
        entry = spec[group]
        for name, meta in entry["files"].items():
            url = entry["url"].format(**meta)
            status = fetch(url, ASSETS / group / name, meta["sha256"])
            print(f"{group}/{name}: {status}, SHA-256 ok")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
