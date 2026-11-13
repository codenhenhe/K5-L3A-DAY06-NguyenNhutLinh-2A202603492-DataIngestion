"""Read source units while preserving their original boundaries."""
import json
import logging
from pathlib import Path
import unicodedata

from .models import DocumentPage

logger = logging.getLogger(__name__)


def normalize_text(text: str) -> str:
    """Normalize Unicode and newlines while preserving paragraph and code layout."""
    text = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
    return "\n".join(line.rstrip() for line in text.split("\n")).strip()


def load_pdf(path: Path, document_id: str, source: str) -> list[DocumentPage]:
    """Read extractable PDF pages, logging physical pages that require OCR."""
    from pypdf import PdfReader

    pages = []
    for number, page in enumerate(PdfReader(path).pages, 1):
        try:
            text = normalize_text(page.extract_text() or "")
        except Exception:
            logger.exception("%s page %d: extraction failed", path, number)
            raise
        if text:
            pages.append(DocumentPage(document_id, source, number, text))
        else:
            logger.warning("%s page %d: no extractable text", path, number)
    return pages


def load_jsonl(path: Path) -> list[DocumentPage]:
    """Load the complete corpus or fail before any existing index is replaced."""
    pages = []
    seen = set()
    with path.open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            try:
                row = json.loads(line)
                document_id, source, page, section, text = (
                    row[field] for field in ("document_id", "source", "page", "section", "text")
                )
                if not all(isinstance(value, str) and value.strip()
                           for value in (document_id, source, section, text)):
                    raise ValueError("document_id, source, section and text must be non-empty strings")
                if not (type(page) is int and page > 0 or isinstance(page, str) and page.strip()):
                    raise ValueError("page must be a positive integer or a non-empty ID")
                key = (document_id, page)
                if key in seen:
                    raise ValueError(f"duplicate document/page {key}")
                text = normalize_text(text)
                if not text:
                    raise ValueError("empty text after normalization")
                seen.add(key)
                metadata = {"section": section}
                if isinstance(row.get("title"), str):
                    metadata["title"] = row["title"]
                pages.append(DocumentPage(document_id, source, page, text, metadata))
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError(f"{path}:{number}: {error}") from error
    if not pages:
        raise ValueError(f"{path}: no source units")
    return pages
