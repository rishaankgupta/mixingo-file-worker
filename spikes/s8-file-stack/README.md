# Spike S-8: file stack

Can the file worker rewrite a PDF's text in place for every script Mixingo outputs, and can Tesseract read scanned pages in those scripts? This is a spike: throwaway code that answers questions before the worker is built. It is not the worker.

## What it runs

| Part | Script | Checks |
|---|---|---|
| A | `rewrite.py` | Builds an English page (three text blocks, an image, line art), removes the text with redactions that keep the image and line art, writes the target text back with PyMuPDF's `insert_htmlbox` and pinned Noto fonts. Checks fit, line alignment, preserved graphics, leftover source text, text extraction, embedded fonts, and that every glyph drawn matches HarfBuzz shaping of the same text with the same font. |
| Probe | `text_layer_probe.py` | Whether copying text out of those PDFs works in MuPDF, PDFium (Chrome, Edge) and pdf.js (Firefox), with and without an `/ActualText` span. |
| B | `ocr.py` | Tesseract script detection (OSD) and character error rate per script, on clean and degraded 200 DPI renders, with Ubuntu's models and the pinned tessdata_best models. |

Targets: Latin (the Roman-script hybrids), Devanagari, Bengali, Malayalam, Tamil, Telugu, Urdu in Nastaliq, Arabic in Naskh. Sample texts are in `samples.py`; they are written by Kiro, not checked by native speakers, and test rendering and OCR only.

## Running it

```sh
python -m pip install --require-hashes --no-deps -r requirements.txt
python fetch_assets.py              # pinned fonts and Tesseract models, SHA-256 checked
python rewrite.py                   # part A; writes out/
python text_layer_probe.py          # set PDFJS_DIR to a folder with pdfjs-dist installed to include pdf.js
python ocr.py                       # part B; needs tesseract on PATH with the osd and language models
```

The GitHub workflow `.github/workflows/spike-s8.yml` runs all three on Ubuntu 24.04 and uploads `out/` as an artifact.

## Pinning

- Python packages: exact versions with every published file hash (`--require-hashes`).
- **PyMuPDF 2.x declares eight dependencies, including onnxruntime and numpy** (about 230 MB installed, for its layout-analysis features). The spike installs it with `--no-deps`, and the features it uses work without them. PyMuPDF 1.28.2 has no dependencies.
- Fonts: Noto, from a pinned commit of `notofonts/notofonts.github.io`, SIL Open Font License 1.1.
- Tesseract best models: a pinned commit of `tesseract-ocr/tessdata_best`, Apache License 2.0.

## Licence

AGPL-3.0-or-later, like the rest of this repository (see `LICENSE`). PyMuPDF is AGPL-licensed.
