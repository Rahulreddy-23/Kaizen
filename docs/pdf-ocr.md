# PDF extraction and local setup

## Recommended setup

From the checkout, run `.\scripts\setup-local.ps1` on Windows or
`bash scripts/setup-local.sh` on macOS/Linux. Add `--check-only` to collect a diagnosis without installs.
The script checks Python, app/package versions, Node/npm, UI build and actual label/drawing OCR. Its
shareable `out/setup-report.json` contains no documents, account information or credentials.

Repairs use a project virtual environment. Missing compatible Python can be downloaded through uv;
missing Node 22 is downloaded from nodejs.org and checked against its official SHA-256 manifest.
These managed runtimes stay in ignored `.kaizen-tools/`; the global PATH is unchanged. An incompatible
old `.venv` is preserved as a backup. The script does not update Git, rewrite reviews, start paid services,
change passwords or upload files. Internet is required only for installing dependencies/runtimes.

If no bootstrap Python exists, the Windows launcher uses winget and the macOS launcher can use an
existing Homebrew installation. On a bare Linux machine, install Python and its matching venv package
with the OS package manager first. Windows corporate PowerShell/installation policy may require IT;
the launcher does not change that policy. Linux shared-library and Windows runtime errors below may
also require IT/system package installation.

## Manual setup

Use Python 3.12 or 3.13. Install from the repository root with the same virtual environment used to
start Kaizen. A normal install now includes the offline OCR engine and bundled models; no separate
Tesseract install, model download at runtime, API key or external AI service is needed.

```bash
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[api]"
.venv/bin/kaizen doctor
.venv/bin/kaizen serve
```

For Windows PowerShell, replace `.venv/bin/python` with `.\.venv\Scripts\python.exe` and
`.venv/bin/kaizen` with `.\.venv\Scripts\kaizen.exe`. The README's `[dev]` install also includes OCR.
The old `[ocr]` extra remains accepted for compatibility.

`kaizen doctor` reads synthetic pixels with each installed engine. At least one must show **READY**.
Tesseract **UNAVAILABLE — not on PATH (optional)** is fine when RapidOCR is ready. A failed check exits
with code 1; an import alone is not treated as proof of working OCR.

## Existing installations

Pull the changes, repeat the install and doctor commands, then restart the running server. Create a new
run from the source documents: existing runs intentionally retain their original extraction and review
history. Updating Python packages does not rewrite saved runs.

OCR models are pinned to the same RapidOCR release on Python 3.12 and 3.13 so a fresh environment does
not silently select different model releases. CI checks installation and real synthetic scans on Linux,
Windows and macOS. This does not establish support for every OS, processor or Python release.

## If installation or OCR fails

- **No OCR engine / missing module:** check that install, doctor and serve use the same `.venv`.
- **Windows DLL load error:** use 64-bit Python and install/repair Microsoft's
  [Visual C++ x64 runtime](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist).
- **Linux `libGL.so.1` / shared-library error:** on Debian/Ubuntu, install `libgl1`, `libglib2.0-0` and
  `libgomp1`. The deployment Docker image already includes these and both OCR engines.
- **Tesseract fails:** check its executable and English (`eng`) language data. Kaizen automatically tries
  the portable engine when the first engine fails or returns no text. `kaizen doctor` identifies the
  engine that failed without opening any customer files.
- **Still unreadable:** retain the warning and inspect the source. Blurred, cropped, low-resolution or
  sideways artwork can remain unreadable. Never treat an OCR failure as proof that a component is absent.

## Extraction behavior

Native PDF text is preferred. Bundled RapidOCR is the default offline engine; Tesseract is the backup. Scanned labels/drawings and labels whose letters are vector outlines use
OCR. A searchable REF/title block alone does not establish that scanned contents/callouts were read.
Coordinates, page references, raw recognized text and field confidence remain attached to the output.
BOM native-text parsing and matching thresholds are unchanged by these OCR setup fixes.

OCR reads local page rasters with local models. ONNX Runtime telemetry is disabled before initialization.
No cloud OCR service is used. Source files are not modified. OCR confidence warnings remain visible for
review; hiding them would not improve extraction accuracy. Leader-line endpoints, photographic placement,
ambiguous text and engineering approval still require a reviewer.

## Missing or merged lines

Outlined drawing letters are re-read in tight row crops when full-page OCR misses a row or loses word
spacing. This uses vector geometry rather than product-specific terms. Photo text is excluded from
callouts when a separate outlined text layer is available; outlined instructions over photos are retained.
English/Spanish continuations stay together. Labels retain continuation sheets without a repeated heading
and explicit quantity/unit entries without a dash. A damaged native label layer may supply spacing where
its characters agree with OCR; it cannot replace OCR characters or quantities.

In a new run, open a label/drawing and select **All recognized text** to inspect headers, notes and text
that did not become comparison entries. Filter by phrase or page, then select a line to highlight its
source. This view is separate from component comparisons and never creates synonyms or approvals.
Older runs retain their original extraction. Full-text capture is not a guarantee that every character was
recognized correctly; unreadable scans and ambiguous identifiers still need source verification.

## Layout and evidence safeguards

Label contents columns are inferred from quantity/unit starters. The full-text view uses those same
boundaries within the contents region, so nearby columns do not become one line. Headers and footers
retain their own layout. A matching native text layer can supply missing spaces in this view; the
selected line also shows the original raw OCR. Letters, identifiers and quantities are never replaced
by this spacing step.

Drawing notes belong to the aligned stack below their heading. They do not cut off a caption in another
column. Wrapped captions can return from a hanging indent to their original edge, keeping English and
Spanish evidence together. Spanish conditional/placement qualifiers and depicted counts are separated
from component wording; meaningful parentheses such as plural suffixes and dimensions are retained.

These changes follow the layout/position approach described in the
[PyMuPDF text extraction documentation](https://pymupdf.readthedocs.io/en/latest/recipes-text.html).
[Tesseract's quality guidance](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html) also identifies
segmentation, region size and image quality as causes of OCR errors. It does not establish that higher
DPI or a different engine will always improve a page. Kaizen uses offline recognition and preserves
source evidence so improvements can be evaluated without sending documents to an external OCR service.

Measure changes against source transcriptions, including character errors, complete entries, separately
retained physical lines, numeric fields and translation association. Keep a separate set of unseen
layouts for independent review. Counts and engine confidence alone do not establish accuracy; visually
ambiguous characters and document-specific engineering conclusions still require verification.
