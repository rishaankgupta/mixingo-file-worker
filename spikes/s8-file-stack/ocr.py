#!/usr/bin/env python3
"""Spike S-8, part B: Tesseract on the pages written by part A.

Needs `tesseract` on PATH with the osd model and the language models of samples.TARGETS
(Ubuntu: tesseract-ocr-osd, tesseract-ocr-hin, ...), and part A's output in OUT_DIR.

For each target page:
  - render it at 200 DPI (design 4.8), once clean and once degraded the way a phone photo or
    cheap scan degrades it (0.7 degree rotation, blur, JPEG quality 45);
  - script detection: tesseract --psm 0 (OSD) on the full page;
  - recognition: each text block cropped and read with --psm 6, with the system models
    (Ubuntu's tessdata_fast) and the pinned tessdata_best models;
  - character error rate (CER): edit distance between the expected and the recognised text,
    NFC, whitespace removed, divided by the expected length.

These pages are synthetic: clean digital text, one font, white background. Real scans are
worse, so the numbers are an upper bound on quality.
"""
from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import pymupdf
from PIL import Image, ImageFilter

from rewrite import ASSETS, OUT, levenshtein, norm
from samples import BLOCK_KEYS, TARGETS

DPI = 200
BEST = ASSETS / "tessdata_best"


def degrade(image: Image.Image) -> Image.Image:
    grey = image.convert("L").rotate(0.7, resample=Image.Resampling.BICUBIC, fillcolor=255)
    blurred = grey.filter(ImageFilter.GaussianBlur(radius=0.7))
    buffer = io.BytesIO()
    blurred.save(buffer, "JPEG", quality=45)
    return Image.open(io.BytesIO(buffer.getvalue()))


def tesseract(image: Path, args: list[str]) -> tuple[str, float]:
    started = time.perf_counter()
    result = subprocess.run(["tesseract", str(image), "stdout", *args], capture_output=True, text=True, timeout=300)
    seconds = time.perf_counter() - started
    if result.returncode != 0:
        return f"ERROR: {result.stderr.strip()[-300:]}", seconds
    return result.stdout, seconds


def osd(image: Path) -> dict[str, Any]:
    out, _ = tesseract(image, ["--psm", "0"])
    script = re.search(r"Script: (\S+)", out)
    confidence = re.search(r"Script confidence: ([\d.]+)", out)
    return {
        "script": script.group(1) if script else out.strip()[:80],
        "confidence": float(confidence.group(1)) if confidence else None,
    }


def cer(expected: str, actual: str) -> float:
    e = norm(expected)
    return round(levenshtein(e, norm(actual)) / max(1, len(e)), 4)


def main() -> int:
    version = subprocess.run(["tesseract", "--version"], capture_output=True, text=True, check=True).stdout.splitlines()[0]
    rewrite = json.loads((OUT / "results-rewrite.json").read_text(encoding="utf-8"))
    rects = {t["key"]: {b["key"]: pymupdf.Rect(b["rect"]) for b in t["blocks"]} for t in rewrite["targets"]}
    scale = DPI / 72
    results = []
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        for target in TARGETS:
            page = pymupdf.open(OUT / f"{target.key}.pdf")[0]
            clean = Image.open(io.BytesIO(page.get_pixmap(dpi=DPI).tobytes("png"))).convert("RGB")
            pages = {"clean": clean, "degraded": degrade(clean)}
            row: dict[str, Any] = {"key": target.key, "lang": target.ocr_lang, "osd": {}, "cer": {}, "seconds": {}}
            for condition, image in pages.items():
                full = work / f"{target.key}-{condition}.png"
                image.save(full)
                row["osd"][condition] = osd(full)
                crops = []
                for key in BLOCK_KEYS:
                    r = rects[target.key][key]
                    crop = image.crop((int(r.x0 * scale) - 8, int(r.y0 * scale) - 8, int(r.x1 * scale) + 8, int(r.y1 * scale) + 8))
                    path = work / f"{target.key}-{condition}-{key}.png"
                    crop.save(path)
                    crops.append((key, path))
                for models, extra in (("fast", []), ("best", ["--tessdata-dir", str(BEST)])):
                    expected, recognised, seconds = "", "", 0.0
                    for key, path in crops:
                        text, spent = tesseract(path, ["-l", target.ocr_lang, "--psm", "6", *extra])
                        expected += target.text(key)
                        recognised += text
                        seconds += spent
                    row["cer"][f"{models}-{condition}"] = cer(expected, recognised)
                    row["seconds"][f"{models}-{condition}"] = round(seconds, 2)
                    if condition == "clean":
                        row.setdefault("sample", {})[models] = recognised.strip().splitlines()[:2]
            results.append(row)

    (OUT / "results-ocr.json").write_text(json.dumps({"tesseract": version, "dpi": DPI, "targets": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{version}, {DPI} DPI. CER: lower is better; 0.02 means 2 wrong characters in 100.")
    print("| Target | Model | OSD clean | OSD degraded | CER fast clean | CER fast degraded | CER best clean | CER best degraded | s fast/best (clean) |")
    print("|---|---|---|---|---|---|---|---|---|")
    for r in results:
        o = r["osd"]
        print(
            f"| {r['key']} | {r['lang']} | {o['clean']['script']} ({o['clean']['confidence']}) | {o['degraded']['script']} ({o['degraded']['confidence']}) "
            f"| {r['cer']['fast-clean']} | {r['cer']['fast-degraded']} | {r['cer']['best-clean']} | {r['cer']['best-degraded']} "
            f"| {r['seconds']['fast-clean']}/{r['seconds']['best-clean']} |"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
