#!/usr/bin/env python3
"""Spike S-8, text-layer probe: can text written by insert_htmlbox be copied out of the PDF again?

Part A showed that the glyphs are right but text extraction of complex scripts is wrong: MuPDF
maps each glyph to Unicode through the font's character map, which has no entry for conjuncts,
ligatures or Arabic positional forms. This probe writes each target's message paragraph twice:
  plain       as insert_htmlbox writes it;
  actualtext  the same, with the new content wrapped in a marked-content span whose /ActualText is
              the paragraph's real text (PDF 2.0, ISO 32000-2, section 14.9.4).
and extracts both with three PDF engines: MuPDF (many apps), PDFium (Chrome, Edge) and pdf.js
(Firefox), if PDFJS_DIR points to a folder with pdfjs-dist installed.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pymupdf
import pypdfium2 as pdfium

from rewrite import FONTS, OUT, css_for, html_for, similarity
from samples import TARGETS

PROBE = OUT / "probe"
RECT = pymupdf.Rect(56, 60, 539, 300)


def actual_text_span(text: str) -> bytes:
    encoded = ("\ufeff" + text).encode("utf-16-be").hex().upper()
    return f"/Span <</ActualText <{encoded}>>> BDC\n".encode("ascii")


def write(target, archive: pymupdf.Archive, with_actual_text: bool) -> tuple[Path, str]:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    xobjects_before = {x[0] for x in page.get_xobjects()}
    contents_before = set(page.get_contents())
    page.insert_htmlbox(RECT, html_for(target, target.message), css=css_for(target, 12), archive=archive)
    where = "none"
    if with_actual_text:
        new_xobjects = [x[0] for x in page.get_xobjects() if x[0] not in xobjects_before]
        new_contents = [x for x in page.get_contents() if x not in contents_before]
        targets = new_xobjects or new_contents
        where = "form xobject" if new_xobjects else "page content stream"
        for xref in targets:
            doc.update_stream(xref, actual_text_span(target.message) + doc.xref_stream(xref) + b"\nEMC\n")
    doc.subset_fonts()
    path = PROBE / f"{target.key}-{'actualtext' if with_actual_text else 'plain'}.pdf"
    path.write_bytes(doc.tobytes(garbage=3, deflate=True))
    return path, where


def pdfium_text(path: Path) -> str:
    document = pdfium.PdfDocument(str(path))
    try:
        return document[0].get_textpage().get_text_bounded()
    finally:
        document.close()


def pdfjs_texts(paths: list[Path]) -> dict[str, str] | None:
    directory = os.environ.get("PDFJS_DIR")
    if not directory:
        return None
    script = Path(__file__).with_name("pdfjs_text.mjs")
    result = subprocess.run(
        ["node", str(script), *map(str, paths)],
        capture_output=True,
        text=True,
        check=True,
        timeout=300,
        env={**os.environ, "PDFJS_DIR": directory},
    )
    return json.loads(result.stdout)


def main() -> int:
    PROBE.mkdir(parents=True, exist_ok=True)
    archive = pymupdf.Archive(str(FONTS))
    rows = []
    for target in TARGETS:
        for variant in (False, True):
            path, where = write(target, archive, variant)
            rows.append({"key": target.key, "variant": "actualtext" if variant else "plain", "path": path, "where": where, "expected": target.message})
    js = pdfjs_texts([row["path"] for row in rows])
    for row in rows:
        row["mupdf"] = similarity(row["expected"], pymupdf.open(row["path"])[0].get_text())
        row["pdfium"] = similarity(row["expected"], pdfium_text(row["path"]))
        row["pdfjs"] = None if js is None else similarity(row["expected"], js[str(row["path"])])

    print("| Target | Text layer | MuPDF | PDFium | pdf.js | ActualText placed in |")
    print("|---|---|---|---|---|---|")
    for row in rows:
        print(f"| {row['key']} | {row['variant']} | {row['mupdf']} | {row['pdfium']} | {row['pdfjs'] if row['pdfjs'] is not None else 'not run'} | {row['where']} |")
    report = [{k: (str(v) if k == "path" else v) for k, v in row.items() if k != "expected"} for row in rows]
    meta = {"pymupdf": pymupdf.__version__, "pypdfium2": getattr(pdfium, "__version__", str(getattr(pdfium, "version", "?")))}
    (OUT / "results-text-layer.json").write_text(json.dumps({"meta": meta, "rows": report}, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
