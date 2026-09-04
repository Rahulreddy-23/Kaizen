import hashlib
from pathlib import Path


def sha256_file(path: Path | str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def document_id(prefix: str, file_sha256: str, path: Path | str) -> str:
    """Stable, unique per file: content hash plus a short hash of the path, so identical files in two SKU
    folders never share an ID."""
    path_digest = hashlib.sha256(str(Path(path).resolve()).encode("utf-8")).hexdigest()[:6]
    return f"{prefix}:{file_sha256[:12]}:{path_digest}"
