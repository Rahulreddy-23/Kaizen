"""Offline OCR for scanned BOMs, labels, and drawings, including damaged label text layers.
Native PDF text is preferred. Tesseract or the bundled RapidOCR engine reads pages locally;
results carry confidence and displayed-page bounding boxes, marked extraction_method='ocr'.

Product-name OCR corrections are loaded from ``ocr_corrections.json`` (same directory) so they can be
edited without touching source code.  Structural spacing rules (digit/CM/X spacing) are kept in code."""

import csv
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import pymupdf

from kaizen.ingest.pdf_words import Word

# ---------------------------------------------------------------------------
# Product-name corrections — loaded from the adjacent JSON file so that new
# brand-name OCR glitches can be added without changing Python source.
# ---------------------------------------------------------------------------
_CORRECTIONS_FILE = Path(__file__).with_name("ocr_corrections.json")


def _load_product_corrections(path: Path = _CORRECTIONS_FILE) -> tuple[tuple[re.Pattern, str], ...]:
    """Read [pattern, replacement] pairs from *path* and compile them."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return tuple((re.compile(entry[0], re.IGNORECASE), entry[1]) for entry in data["corrections"])


_PRODUCT_CORRECTIONS: tuple[tuple[re.Pattern, str], ...] = _load_product_corrections()

# ---------------------------------------------------------------------------
# Structural spacing rules — regex mechanics, not brand-name lists.
# These fix systematic OCR joining artefacts (digit–unit, dimension notation).
# ---------------------------------------------------------------------------
_STRUCTURAL_CORRECTIONS: tuple[tuple[re.Pattern, str], ...] = (
    (re.compile(r"(\d+)per(?=pouch\b)", re.IGNORECASE), r"\1 per "),
    (re.compile(r"(\d%?)(?=Isopropyl)", re.IGNORECASE), r"\1 "),
    (re.compile(r"(?<=Isopropyl)(?=Alcohol)", re.IGNORECASE), " "),
    (re.compile(r"(?<=\d)(?=Isopropyl)", re.IGNORECASE), " "),
    (re.compile(r"(?<=pouch)(?=\d|Each)", re.IGNORECASE), " "),
    (re.compile(r"(\d+(?:\.\d+)?)(CM)(?=X|\d)", re.IGNORECASE), r"\1\2 "),
    (re.compile(r"(?<=\d)(?=CM\b)", re.IGNORECASE), " "),
    (re.compile(r"(?<=X)(?=\d)", re.IGNORECASE), " "),
)

_LABEL_WORDS = frozenset(
    """
    ABSORBENT ADHESIVE ALCOHOL AMPULE APPLICATOR ASSEMBLY ASPIRATION BAND BARRIER BENDABLE BLUE
    BOUFFANT CAP CATHETER CHLORAPREP CONTROL DEVICE DILATOR DRAPE DRESSING DUAL EACH ECG ELECTRODE
    ELECTRODES END FENESTRATED FLEXURA FUNNEL GAUZE GLOVE GLOVES GUIDE GUIDEWIRE HOLDER HYPODERMIC
    ID INTRODUCER ISOPROPYL IV LEAD LEADS LENGTH LID LUMEN MASK MEASURE MEASURING MICROINTRODUCER
    NEEDLE NITINOL OD PERIPHERAL PICC PROTECTIVE SAFETY SALINE SCALPEL SHERLOCK SOLUTION STRAIGHT
    STYLET SURGICAL SYRINGE TAPE TIP TOURNIQUET TRIMMING VESSEL WITH
    """.split()
)
_FUSED_LABEL_TOKEN_RE = re.compile(r"\b[A-Za-z]{8,}\b")


def _split_fused_label_token(token: str) -> str:
    upper = token.upper()
    if upper in _LABEL_WORDS:
        return token

    # Count complete segmentations from right to left, capped at two: only a unique
    # path is safe to recover. Bound each lookup by the longest approved word and
    # avoid recursion so even a long OCR join cannot exhaust Python's call stack.
    size = len(token)
    max_word_length = max(map(len, _LABEL_WORDS))
    counts = [0] * (size + 1)
    next_end = [0] * size
    counts[size] = 1
    for start in range(size - 1, -1, -1):
        for end in range(start + 2, min(size, start + max_word_length) + 1):
            if counts[end] and upper[start:end] in _LABEL_WORDS:
                next_end[start] = end
                counts[start] = min(2, counts[start] + counts[end])
                if counts[start] == 2:
                    break
    if counts[0] != 1:
        return token
    parts = []
    start = 0
    while start < size:
        end = next_end[start]
        parts.append(token[start:end])
        start = end
    return " ".join(parts)


def correct_fused_label_words(text: str) -> str:
    """Split only uniquely segmented OCR tokens made entirely of known label terms."""
    return _FUSED_LABEL_TOKEN_RE.sub(lambda match: _split_fused_label_token(match.group()), text)


def correct_ocr_text(text: str) -> str:
    for pattern, replacement in _PRODUCT_CORRECTIONS:
        text = pattern.sub(replacement, text)
    for pattern, replacement in _STRUCTURAL_CORRECTIONS:
        text = pattern.sub(replacement, text)
    return text


@dataclass
class OcrResult:
    words: list[tuple[float, float, float, float, str, float]] = field(default_factory=list)  # x0,y0,x1,y1 (PDF points), text, confidence
    engine: str = ""
    dpi: int = 200
    notices: list[str] = field(default_factory=list)


_LOCK = threading.RLock()
_CACHE: OrderedDict[str, OcrResult] = OrderedDict()


OCR_SETUP_HELP = 'Run `kaizen doctor` in the app virtual environment. From the project folder, repair with `python -m pip install -e ".[api]"`, then restart Kaizen.'


class OcrError(RuntimeError):
    """A safe installation/runtime diagnostic, without document text or subprocess output."""


def _rapid_session_options():
    """Bound inference threads to fit desktop CPUs and the single-core pilot."""
    import onnxruntime

    options = onnxruntime.SessionOptions()
    # Hosted image sets OMP_NUM_THREADS=1; desktops use at most four workers.
    try:
        threads = int(os.environ.get("OMP_NUM_THREADS", min(4, os.cpu_count() or 1)))
    except ValueError:
        threads = 1
    options.intra_op_num_threads = max(1, min(4, threads))
    options.inter_op_num_threads = 1
    options.add_session_config_entry("session.intra_op.allow_spinning", "0")
    return options


def _rapid_module():
    # Set before importing ONNX Runtime: its initialization may otherwise enable telemetry.
    # OCR and its bundled models must remain offline, including on desktop installations.
    os.environ["ORT_DISABLE_TELEMETRY"] = "1"
    import onnxruntime

    onnxruntime.disable_telemetry_events()
    import rapidocr_onnxruntime
    from rapidocr_onnxruntime import utils

    # Pinned RapidOCR 1.2.3 does not expose thread options in its constructor.
    # Configure its session-options factory before it constructs any detector,
    # recognizer or classifier. This leaves ONNX Runtime's global API untouched.
    utils.SessionOptions = _rapid_session_options
    return rapidocr_onnxruntime


def available_engines() -> list[str]:
    """Discover candidates locally; `ocr_diagnostics` verifies actual recognition."""
    engines = []
    try:
        _rapid_module()
        engines.append("rapidocr-onnxruntime")
    except Exception:
        pass
    if shutil.which("tesseract"):
        engines.append("tesseract")
    return engines


def ocr_available() -> bool:
    return bool(available_engines())


@lru_cache(maxsize=2)
def _rapid_engine(single_line: bool = False):
    RapidOCR = _rapid_module().RapidOCR

    # The default detector downsizes engineering sheets to 736px, losing small callouts.
    # Passing model_path also supports RapidOCR 1.2's parameter updater.
    return RapidOCR(det_model_path=None, det_limit_side_len=2400, det_limit_type="max", use_text_det=not single_line, text_score=0.0 if single_line else 0.5)


def ocr_page(page: pymupdf.Page, dpi: int = 240, *, clip: pymupdf.Rect | None = None, single_line: bool = False) -> OcrResult:
    """Offline OCR with word confidence and rendered-page coordinates in PDF points.

    Bundled RapidOCR is preferred consistently on desktop and hosted installs;
    Tesseract is an optional backup. A bounded content cache reuses a shared drawing without retaining rasters.
    Failed or empty recognition falls back to the next engine. If all engines fail,
    parsers report an unreadable page explicitly.
    """
    engines = available_engines()
    if not engines:
        raise OcrError(f"No offline OCR engine is usable. {OCR_SETUP_HELP}")
    rect = clip or page.rect
    pix = page.get_pixmap(dpi=dpi, clip=rect, colorspace=pymupdf.csRGB, alpha=False)
    png = pix.tobytes("png")
    key = hashlib.sha256(png + str((dpi, tuple(rect), page.rotation, engines, single_line)).encode()).hexdigest()
    with _LOCK:
        if key in _CACHE:
            _CACHE.move_to_end(key)
            cached = _CACHE[key]
            return OcrResult(words=list(cached.words), engine=cached.engine, dpi=dpi, notices=list(cached.notices))
        failures = []
        empty = []
        for engine in engines:
            try:
                result = _recognize(png, engine, single_line)
            except Exception as exc:
                # Missing English data, a broken executable or a failed model must not
                # prevent a second installed offline engine from reading the page.
                failures.append(f"{engine}: {type(exc).__name__}")
                continue
            if result:
                break
            empty.append(engine)
        else:
            if not empty:
                raise OcrError(f"All offline OCR engines failed ({'; '.join(failures)}). {OCR_SETUP_HELP}")
            engine, result = empty[-1], []
        words = []
        for x0, y0, x1, y1, t, conf in result:
            # Pixmap origin includes clip offsets. Keep the displayed orientation for
            # layout parsing and evidence overlays, including rotated scans.
            box = pymupdf.Rect((x0 + pix.x) * 72 / dpi, (y0 + pix.y) * 72 / dpi, (x1 + pix.x) * 72 / dpi, (y1 + pix.y) * 72 / dpi)
            words.append((box.x0, box.y0, box.x1, box.y1, t, conf))
        notices = [f"OCR fallback used {engine} after {'; '.join(failures)}"] if failures and words else []
        out = OcrResult(words=words, engine=engine, dpi=dpi, notices=notices)
        # Do not cache failed/empty recognition: repaired engines can retry immediately.
        if words:
            _CACHE[key] = out
            if len(_CACHE) > 32:
                _CACHE.popitem(last=False)
        return OcrResult(words=list(out.words), engine=out.engine, dpi=dpi, notices=list(out.notices))


def ocr_diagnostics() -> list[dict[str, str | bool]]:
    """Read synthetic pixels with each engine; never opens a user's documents."""
    checks = []
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=600, height=140)
        page.insert_text((30, 85), "KAIZEN TEST 123", fontsize=36)
        png = page.get_pixmap(dpi=150).tobytes("png")
    for engine in ("tesseract", "rapidocr-onnxruntime"):
        if engine == "tesseract" and not shutil.which("tesseract"):
            checks.append({"engine": engine, "ready": False, "detail": "not on PATH (optional)"})
            continue
        try:
            text = " ".join(w[4] for w in _recognize(png, engine, False)).upper()
            ready = "KAIZEN" in text and "123" in text
            detail = "synthetic scan read successfully" if ready else "could not read the synthetic scan"
        except Exception as exc:
            ready = False
            detail = type(exc).__name__
            if engine == "tesseract":
                detail += " (check the executable and English language data)"
        checks.append({"engine": engine, "ready": ready, "detail": detail})
    return checks


def _recognize(png: bytes, engine: str, single_line: bool) -> list[tuple]:
    if engine == "tesseract":
        proc = subprocess.run(
            ["tesseract", "stdin", "stdout", "-l", "eng", "--psm", "7" if single_line else "11", "tsv"],
            input=png, capture_output=True, timeout=120, check=True,
        )
        out = []
        # TSV is not CSV: an inch mark or quote in a word must not start a quoted field.
        for row in csv.DictReader(io.StringIO(proc.stdout.decode("utf-8")), delimiter="\t", quoting=csv.QUOTE_NONE):
            if row.get("level") != "5" or not (row.get("text") or "").strip():
                continue
            x, y, w, h = (float(row[k]) for k in ("left", "top", "width", "height"))
            out.append((x, y, x + w, y + h, row["text"], max(0, min(1, float(row["conf"]) / 100))))
        return out
    result, _ = _rapid_engine(single_line)(png)
    words: list[tuple[float, float, float, float, str, float]] = []
    for box, text, conf in result or []:
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
        # OCR returns line-level boxes; split into words proportionally so downstream column logic still works
        tokens = str(text).split()
        if not tokens:
            continue
        total = sum(len(t) for t in tokens) + max(len(tokens) - 1, 0)
        cursor = 0
        for t in tokens:
            left = x0 + (x1 - x0) * cursor / total
            right = x0 + (x1 - x0) * (cursor + len(t)) / total
            words.append((left, y0, right, y1, t, float(conf)))
            cursor += len(t) + 1
    return words


def ocr_words(result: OcrResult) -> list[Word]:
    return [Word(text=t, x0=x0, y0=y0, x1=x1, y1=y1, block=0, line=i, word_no=0, confidence=c) for i, (x0, y0, x1, y1, t, c) in enumerate(result.words)]


def ocr_min_confidence(result: OcrResult) -> float:
    return min((c for *_, c in result.words), default=1.0)
