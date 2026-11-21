# mixingo-file-worker

The sandboxed document worker for [Mixingo](https://www.mixingo.dev): it inspects uploaded files, extracts their text, renders scanned pages for OCR, and rebuilds the translated document (TXT, DOCX, EPUB, PDF). It runs without internet access and exchanges data with the rest of Mixingo only through files and a versioned JSON contract.

**Status:** not built yet. `spikes/` holds throwaway experiments that answer design questions before the worker is written.

| Folder | Contents |
|---|---|
| `spikes/s8-file-stack/` | Spike S-8: in-place PDF rewriting for eight scripts, copy-and-paste of the result, and Tesseract OCR |

## Licence

Copyright (C) 2026 Rishaank Gupta

This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program (`LICENSE`). If not, see <https://www.gnu.org/licenses/>.

Bundled or downloaded fonts and models keep their own licences: Noto fonts under the SIL Open Font License 1.1, Tesseract models under the Apache License 2.0.
