#!/usr/bin/env python3
"""Spike S-8, part A: rewrite a PDF's text in place, once per target script.

For each target in samples.TARGETS:
  1. Build the English source page: three text blocks, a raster image and vector line art.
  2. Find the text blocks and the free space below each one, down to the next text block, image or
     thin line, the way the worker has to without knowing the layout.
  3. Remove the source text with redactions that keep images and line art (design 4.8).
  4. Write the target text into that space with insert_htmlbox and a bundled Noto font, shrinking
     the text to 60% at most.
  5. Check: images and line art unchanged; no source text left; the text can be extracted again;
     the embedded fonts are the pinned files; the glyphs drawn match HarfBuzz shaping of the same
     text with the same font; vertical mark positioning is kept; nothing overflows; file sizes.

Outputs in OUT_DIR (default ./out): source.pdf, <key>.pdf, <key>.png, sheet.png and
results-rewrite.json. Exit status 1 if a check fails.
"""
from __future__ import annotations

import collections
import hashlib
import html
import io
import json
import os
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any

import pymupdf
import uharfbuzz as hb
from PIL import Image, ImageDraw

from samples import BLOCK_KEYS, SOURCE, TARGETS, Target

HERE = Path(__file__).resolve().parent
ASSETS = Path(os.environ.get("ASSETS_DIR", HERE / "assets"))
FONTS = ASSETS / "fonts"
OUT = Path(os.environ.get("OUT_DIR", HERE / "out"))

SCALE_LOW = 0.6  # design 4.8: shrink to 60% at most
LATIN_FONT = "NotoSans-Regular.ttf"
PAGE = pymupdf.Rect(0, 0, 595, 842)  # A4
FRAME = pymupdf.Rect(36, 36, 559, 806)
RULE_Y = 118
IMAGE_RECT = pymupdf.Rect(56, 345, 216, 435)
LAYOUT = {  # where the source text goes, and its size in points
    "title": (pymupdf.Rect(56, 60, 539, 104), 20),
    "message": (pymupdf.Rect(56, 132, 539, 330), 12),
    "stress": (pymupdf.Rect(56, 452, 539, 600), 12),
}
SOURCE_MARK = "Zqxwv"


# ---------------------------------------------------------------- helpers


def norm(text: str) -> str:
    """NFC with all whitespace removed, for comparisons that ignore line breaks."""
    return "".join(ch for ch in unicodedata.normalize("NFC", text) if not ch.isspace())


def levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb)))
        previous = current
    return previous[-1]


def similarity(expected: str, actual: str) -> float:
    e, a = norm(expected), norm(actual)
    return round(1 - levenshtein(e, a) / max(1, len(e)), 4)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def family_of(font_file: str) -> str:
    return font_file.removesuffix(".ttf").removesuffix("-Regular")


def same_font(span_font: str, family: str) -> bool:
    name = span_font.split("+", 1)[-1].replace(" ", "").replace("-Regular", "")
    return name == family


def rect_list(rect: pymupdf.Rect) -> list[float]:
    return [round(v, 2) for v in rect]


# ---------------------------------------------------------------- source page


def gradient_png() -> bytes:
    image = Image.new("RGB", (160, 90))
    pixels = image.load()
    assert pixels is not None
    for x in range(160):
        for y in range(90):
            pixels[x, y] = (40 + x, 80 + y, 200 - x // 2)
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def build_source() -> pymupdf.Document:
    doc = pymupdf.open()
    page = doc.new_page(width=PAGE.width, height=PAGE.height)
    page.draw_rect(FRAME, color=(0.2, 0.3, 0.6), width=1.5)
    page.draw_line(pymupdf.Point(56, RULE_Y), pymupdf.Point(539, RULE_Y), color=(0.2, 0.3, 0.6), width=1)
    page.insert_image(IMAGE_RECT, stream=gradient_png())
    for key in BLOCK_KEYS:
        rect, size = LAYOUT[key]
        if page.insert_textbox(rect, SOURCE[key], fontname="helv", fontsize=size) < 0:
            raise SystemExit(f"source block {key} does not fit")
    return doc


# ---------------------------------------------------------------- layout analysis


def source_blocks(page: pymupdf.Page) -> dict[str, dict[str, Any]]:
    """Text blocks of the page, merged per layout area, with the largest font size seen."""
    found: dict[str, dict[str, Any]] = {}
    for block in page.get_text("dict")["blocks"]:
        if block["type"] != 0:
            continue
        bbox = pymupdf.Rect(block["bbox"])
        key = next((k for k, (area, _) in LAYOUT.items() if area.contains(bbox.tl + (bbox.br - bbox.tl) * 0.5)), None)
        if key is None:
            raise SystemExit(f"unexpected text block at {bbox}")
        sizes = [span["size"] for line in block["lines"] for span in line["spans"]]
        entry = found.setdefault(key, {"bbox": pymupdf.Rect(bbox), "size": 0.0})
        entry["bbox"] |= bbox
        entry["size"] = max(entry["size"], *sizes)
    missing = set(BLOCK_KEYS) - set(found)
    if missing:
        raise SystemExit(f"source blocks not found: {sorted(missing)}")
    return found


def obstacles(page: pymupdf.Page, blocks: dict[str, dict[str, Any]]) -> list[pymupdf.Rect]:
    rects = [pymupdf.Rect(b["bbox"]) for b in blocks.values()]
    rects += [pymupdf.Rect(info["bbox"]) for info in page.get_image_info()]
    for drawing in page.get_drawings():
        r = pymupdf.Rect(drawing["rect"])
        if r.height < 3 or r.width < 3:  # rules and thin lines; frames around the page are not obstacles
            rects.append(r)
    return rects


def free_space(block: pymupdf.Rect, others: list[pymupdf.Rect], right: float) -> pymupdf.Rect:
    below = [o.y0 for o in others if o.y0 >= block.y1 - 0.5 and o.x1 > block.x0 and o.x0 < right]
    bottom = min([*below, FRAME.y1 - 20]) - 4
    return pymupdf.Rect(block.x0, block.y0, max(block.x1, right), max(block.y1, bottom))


# ---------------------------------------------------------------- shaping reference


class Shaper:
    def __init__(self) -> None:
        self.fonts: dict[str, hb.Font] = {}

    def font(self, file: str) -> hb.Font:
        if file not in self.fonts:
            self.fonts[file] = hb.Font(hb.Face(hb.Blob.from_file_path(str(FONTS / file))))
        return self.fonts[file]

    def shape(self, file: str, text: str, lang: str | None) -> tuple[list[int], list[int]]:
        buffer = hb.Buffer()
        buffer.add_str(unicodedata.normalize("NFC", text))
        buffer.guess_segment_properties()
        if lang is not None:
            buffer.language = lang
        hb.shape(self.font(file), buffer, {})
        return [g.codepoint for g in buffer.glyph_infos], [p.y_offset for p in buffer.glyph_positions]

    def glyph(self, file: str, codepoint: int) -> int | None:
        return self.font(file).get_nominal_glyph(codepoint)


def shaping_report(page: pymupdf.Page, target: Target, shaper: Shaper) -> dict[str, Any]:
    family = family_of(target.font)
    space = shaper.glyph(target.font, 0x20)
    circle = shaper.glyph(target.font, 0x25CC)

    pdf_glyphs: list[int] = []
    notdef = 0
    for span in page.get_texttrace():
        if not same_font(span["font"], family):
            continue
        for char in span["chars"]:
            if char[1] == space:
                continue
            if char[1] == 0:
                notdef += 1
            pdf_glyphs.append(char[1])

    report: dict[str, Any] = {"pdf_glyphs": len(pdf_glyphs), "notdef_in_pdf": notdef}
    for variant, lang in (("with_lang", target.lang), ("without_lang", None)):
        hb_glyphs: list[int] = []
        for key in BLOCK_KEYS:
            gids, _ = shaper.shape(target.font, target.text(key), lang)
            hb_glyphs += [gid for gid in gids if gid not in (0, space)]
        report[variant] = {
            "hb_glyphs": len(hb_glyphs),
            "same_multiset": collections.Counter(hb_glyphs) == collections.Counter(pdf_glyphs),
            # Order as listed by MuPDF's text trace; differs where the trace groups glyphs
            # differently from HarfBuzz's output order. Informational only.
            "same_sequence": None if target.rtl else hb_glyphs == pdf_glyphs,
            "dotted_circles_hb": hb_glyphs.count(circle) if circle else 0,
        }
        if not report[variant]["same_multiset"]:
            diff = collections.Counter(hb_glyphs)
            diff.subtract(collections.Counter(pdf_glyphs))
            report[variant]["glyph_count_difference"] = {str(k): v for k, v in diff.items() if v}
    report["dotted_circles_pdf"] = pdf_glyphs.count(circle) if circle else 0
    return report


# ---------------------------------------------------------------- rewrite


def visual_lines(page: pymupdf.Page, rect: pymupdf.Rect) -> list[pymupdf.Rect]:
    """Extracted lines merged into visual lines. Bidi runs (digits inside Arabic) and Nastaliq's
    sloping words come out as several lines with different baselines, so lines that overlap
    vertically by more than half their height are merged."""
    pieces = sorted(
        (pymupdf.Rect(line["bbox"]) for block in page.get_text("dict", clip=rect)["blocks"] if block["type"] == 0 for line in block["lines"]),
        key=lambda r: (r.y0 + r.y1) / 2,
    )
    merged: list[pymupdf.Rect] = []
    for piece in pieces:
        last = merged[-1] if merged else None
        if last is not None and min(last.y1, piece.y1) - max(last.y0, piece.y0) > 0.5 * min(last.height, piece.height):
            merged[-1] = last | piece
        else:
            merged.append(pymupdf.Rect(piece))
    return merged


def start_aligned(page: pymupdf.Page, rect: pymupdf.Rect, rtl: bool, tolerance: float = 4.0) -> bool:
    """Every visual line starts at the block's start edge: left for LTR, right for RTL."""
    lines = visual_lines(page, rect)
    if not lines:
        return False
    if rtl:
        return all(abs(line.x1 - rect.x1) <= tolerance for line in lines)
    return all(abs(line.x0 - rect.x0) <= tolerance for line in lines)


def css_for(target: Target, size: float) -> str:
    # MuPDF mirrors text-align inside right-to-left paragraphs: "right" puts the lines on the left.
    # With dir="rtl" and no text-align, lines start at the right edge, as they should.
    direction = "direction: rtl;" if target.rtl else "text-align: left;"
    return (
        f"@font-face {{ font-family: target; src: url({target.font}); }}\n"
        f"@font-face {{ font-family: latin; src: url({LATIN_FONT}); }}\n"
        f"p {{ font-family: target, latin; font-size: {size}pt; line-height: {target.line_height};"
        f" margin: 0; color: #111111; {direction} }}\n"
    )


def html_for(target: Target, text: str) -> str:
    direction = ' dir="rtl"' if target.rtl else ""
    return f'<p lang="{target.lang}"{direction}>{html.escape(text)}</p>'


def rewrite(source_pdf: bytes, target: Target, shaper: Shaper, archive: pymupdf.Archive) -> dict[str, Any]:
    started = time.perf_counter()
    doc = pymupdf.open("pdf", source_pdf)
    page = doc[0]

    images_before = sorted(rect_list(pymupdf.Rect(i["bbox"])) for i in page.get_image_info())
    drawings_before = sorted(rect_list(pymupdf.Rect(d["rect"])) for d in page.get_drawings())
    blocks = source_blocks(page)
    others = obstacles(page, blocks)
    right = max(b["bbox"].x1 for b in blocks.values())
    spaces = {key: free_space(b["bbox"], [o for o in others if o != b["bbox"]], right) for key, b in blocks.items()}

    for block in blocks.values():
        page.add_redact_annot(block["bbox"], fill=False)
    page.apply_redactions(
        images=pymupdf.PDF_REDACT_IMAGE_NONE,
        graphics=pymupdf.PDF_REDACT_LINE_ART_NONE,
        text=pymupdf.PDF_REDACT_TEXT_REMOVE,
    )

    block_reports = []
    for key in BLOCK_KEYS:
        rect = spaces[key]
        spare, scale = page.insert_htmlbox(
            rect,
            html_for(target, target.text(key)),
            css=css_for(target, blocks[key]["size"]),
            archive=archive,
            scale_low=SCALE_LOW,
        )
        block_reports.append({
            "key": key,
            "rect": rect_list(rect),
            "size": round(blocks[key]["size"], 2),
            "spare": round(spare, 2),
            "scale": round(scale, 3),
            "overflow": spare < 0,
            "lines_start_aligned": start_aligned(page, rect, target.rtl),
        })
    seconds = time.perf_counter() - started

    text = page.get_text()
    expected = "".join(target.text(key) for key in BLOCK_KEYS)
    fonts = []
    asset_hashes = {meta: name for name in FONTS.iterdir() if name.suffix == ".ttf" for meta in [sha256(name.read_bytes())]}
    for xref, _ext, _type, basefont, *_ in page.get_fonts(full=True):
        content = doc.extract_font(xref)[3]
        fonts.append({"name": basefont, "pinned_file": asset_hashes.get(sha256(content)).name if sha256(content) in asset_hashes else None})

    result: dict[str, Any] = {
        "key": target.key,
        "label": target.label,
        "font": target.font,
        "blocks": block_reports,
        "images_preserved": sorted(rect_list(pymupdf.Rect(i["bbox"])) for i in page.get_image_info()) == images_before,
        "line_art_preserved": sorted(rect_list(pymupdf.Rect(d["rect"])) for d in page.get_drawings()) == drawings_before,
        "source_text_left": SOURCE_MARK in text,
        "extract_similarity": similarity(expected, text),
        "fonts": fonts,
        "shaping": shaping_report(page, target, shaper),
        "rewrite_seconds": round(seconds, 3),
    }

    full = doc.tobytes(garbage=3, deflate=True)
    result["bytes_full"] = len(full)
    try:
        doc.subset_fonts()
        subset = doc.tobytes(garbage=3, deflate=True)
        result["bytes_subset"] = len(subset)
        reopened = pymupdf.open("pdf", subset)
        result["extract_similarity_after_subset"] = similarity(expected, reopened[0].get_text())
        (OUT / f"{target.key}.pdf").write_bytes(subset)
    except Exception as error:  # noqa: BLE001 - a spike records every failure
        result["subset_error"] = f"{type(error).__name__}: {error}"
        (OUT / f"{target.key}.pdf").write_bytes(full)

    page.get_pixmap(dpi=100).save(OUT / f"{target.key}.png")
    return result


# ---------------------------------------------------------------- report


def failures(result: dict[str, Any]) -> list[str]:
    problems = []
    if not result["images_preserved"]:
        problems.append("images changed")
    if not result["line_art_preserved"]:
        problems.append("line art changed")
    if result["source_text_left"]:
        problems.append("source text left")
    if any(b["overflow"] for b in result["blocks"]):
        problems.append("overflow")
    if not all(b["lines_start_aligned"] for b in result["blocks"]):
        problems.append("lines not aligned to the start edge")
    shaping = result["shaping"]
    if not (shaping["with_lang"]["same_multiset"] or shaping["without_lang"]["same_multiset"]):
        problems.append("glyphs differ from HarfBuzz")
    if shaping["notdef_in_pdf"] or shaping["dotted_circles_pdf"]:
        problems.append("missing glyphs or dotted circles")
    if not any(f["pinned_file"] for f in result["fonts"]):
        problems.append("pinned font not embedded")
    return problems


def contact_sheet(results: list[dict[str, Any]]) -> None:
    rows = []
    for result in results:
        doc = pymupdf.open(OUT / f"{result['key']}.pdf")
        page = doc[0]
        top = pymupdf.Rect(result["blocks"][1]["rect"]).y0
        clip_message = pymupdf.Rect(40, top - 4, 555, top + 64)
        clip_stress = pymupdf.Rect(pymupdf.Rect(result["blocks"][2]["rect"]))
        clip_stress.y1 = clip_stress.y0 + 80
        pieces = [page.get_pixmap(dpi=144, clip=clip).tobytes("png") for clip in (clip_message, clip_stress)]
        images = [Image.open(io.BytesIO(p)).convert("RGB") for p in pieces]
        width = max(i.width for i in images)
        row = Image.new("RGB", (width, 28 + sum(i.height for i in images)), "white")
        ImageDraw.Draw(row).text((8, 6), f"{result['key']}: {result['label']}", fill=(180, 0, 0))
        y = 28
        for image in images:
            row.paste(image, (0, y))
            y += image.height
        rows.append(row)
    sheet = Image.new("RGB", (max(r.width for r in rows), sum(r.height + 6 for r in rows)), (220, 220, 220))
    y = 0
    for row in rows:
        sheet.paste(row, (0, y))
        y += row.height + 6
    sheet.save(OUT / "sheet.png")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    source = build_source()
    source_pdf = source.tobytes(garbage=3, deflate=True)
    (OUT / "source.pdf").write_bytes(source_pdf)
    archive = pymupdf.Archive(str(FONTS))
    shaper = Shaper()
    results = []
    for target in TARGETS:
        result = rewrite(source_pdf, target, shaper, archive)
        result["problems"] = failures(result)
        results.append(result)
    contact_sheet(results)

    meta = {
        "pymupdf": pymupdf.__version__,
        "mupdf": getattr(pymupdf, "mupdf_version", "?"),
        "uharfbuzz": hb.__version__,
        "python": sys.version.split()[0],
    }
    (OUT / "results-rewrite.json").write_text(json.dumps({"meta": meta, "targets": results}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"PyMuPDF {meta['pymupdf']} (MuPDF {meta['mupdf']}), uharfbuzz {meta['uharfbuzz']}, Python {meta['python']}")
    print("| Target | Fit (min scale) | Aligned | Images, line art | Source left | Extract | After subset | Glyphs PDF/HB | Same glyphs | Same order | Dotted circles PDF/HB | Size full/subset KB | s | Problems |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in results:
        s = r["shaping"]
        best = s["with_lang"] if s["with_lang"]["same_multiset"] or not s["without_lang"]["same_multiset"] else s["without_lang"]
        print(
            f"| {r['key']} | {'overflow' if any(b['overflow'] for b in r['blocks']) else 'yes'} ({min(b['scale'] for b in r['blocks'])}) "
            f"| {all(b['lines_start_aligned'] for b in r['blocks'])} "
            f"| {r['images_preserved'] and r['line_art_preserved']} | {r['source_text_left']} | {r['extract_similarity']} "
            f"| {r.get('extract_similarity_after_subset', r.get('subset_error'))} | {s['pdf_glyphs']}/{best['hb_glyphs']} "
            f"| with lang {s['with_lang']['same_multiset']}, without {s['without_lang']['same_multiset']} | {best['same_sequence']} "
            f"| {s['dotted_circles_pdf']}/{best['dotted_circles_hb']} | {r['bytes_full'] // 1024}/{r.get('bytes_subset', 0) // 1024} "
            f"| {r['rewrite_seconds']} | {', '.join(r['problems']) or '—'} |"
        )
    return 1 if any(r["problems"] for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
