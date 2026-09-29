"""Extract plain text from an uploaded resume so matching can run.

The binary still lives in S3 (or the local fallback). Only a truncated text
extract is stored on the application row — enough for TF-IDF, never a second
copy of the file.
"""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from app.core.logging import get_logger

logger = get_logger("app.resume_text")

MAX_CHARS = 50_000
_WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
_PRINTABLE = re.compile(r"[A-Za-z][A-Za-z0-9+.#\-]{1,}")


def extract_resume_text(filename: str, data: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    try:
        if suffix == ".pdf":
            raw = _from_pdf(data)
        elif suffix == ".docx":
            raw = _from_docx(data)
        elif suffix == ".doc":
            raw = _from_legacy_doc(data)
        else:
            raw = ""
    except Exception:  # pragma: no cover - extraction must never fail an apply
        logger.warning("resume text extraction failed", extra={"extra_fields": {"filename": filename}})
        return ""
    return " ".join(raw.split())[:MAX_CHARS]


def _from_pdf(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages)


def _from_docx(data: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        xml = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    return " ".join(node.text or "" for node in root.findall(".//w:t", _WORD_NS))


def _from_legacy_doc(data: bytes) -> str:
    """Best-effort: OLE .doc is not a text format. Pull printable tokens."""
    decoded = data.decode("latin-1", errors="ignore")
    return " ".join(_PRINTABLE.findall(decoded))
