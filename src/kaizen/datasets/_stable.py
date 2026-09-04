"""Make generated files byte-for-byte reproducible: fixed PDF trailer IDs and fixed zip timestamps."""

import hashlib
import re
import zipfile
from pathlib import Path

# MuPDF writes each trailer ID element either as a hex string <...> or as a literal string (...).
_ID_ELEM = rb"(?:<[0-9A-Fa-f]+>|\((?:\\.|[^\\)])*\))"
_ID_RE = re.compile(rb"/ID\[\s*" + _ID_ELEM + rb"\s*" + _ID_ELEM + rb"\s*\]")
_ZIP_TIME = (2026, 9, 3, 0, 0, 0)
_CORE_TS_RE = re.compile(rb"(<dcterms:(?:created|modified)[^>]*>)[^<]*(</dcterms:(?:created|modified)>)")
_CORE_TS = b"2026-09-03T00:00:00Z"


def stabilize_pdf(path: Path) -> None:
    data = path.read_bytes()
    m = _ID_RE.search(data)
    if not m:
        return
    digest = hashlib.sha256(data[: m.start()] + data[m.end():]).hexdigest()[:32].upper().encode()
    stable = b"/ID[<" + digest + b"><" + digest + b">]"
    path.write_bytes(data[: m.start()] + stable + data[m.end():])


def stabilize_zip(path: Path) -> None:
    with zipfile.ZipFile(path) as src:
        entries = [(info, src.read(info.filename)) for info in src.infolist()]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as dst:
        for info, payload in entries:
            if info.filename == "docProps/core.xml":
                payload = _CORE_TS_RE.sub(lambda m: m.group(1) + _CORE_TS + m.group(2), payload)
            zi = zipfile.ZipInfo(info.filename, date_time=_ZIP_TIME)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = info.external_attr
            dst.writestr(zi, payload)
