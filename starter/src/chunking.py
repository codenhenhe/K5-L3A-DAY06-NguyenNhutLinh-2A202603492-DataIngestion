"""Split source text into contiguous, traceable chunks."""
import json
import re
from uuid import NAMESPACE_URL, uuid5

from .models import Chunk, DocumentPage


def _chunk(page: DocumentPage, start: int, end: int) -> Chunk:
    key = json.dumps([page.document_id, page.page, start, end], ensure_ascii=False)
    metadata = {**page.metadata, "char_start": start, "char_end": end}
    return Chunk(
        str(uuid5(NAMESPACE_URL, key)), page.document_id, page.source,
        page.page, page.text[start:end], metadata,
    )


def fixed_size(page: DocumentPage, size: int, overlap: int) -> list[Chunk]:
    """Return character windows with overlap and no redundant final window."""
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError("fixed size must be positive and overlap must be in [0, size)")
    chunks = []
    for start in range(0, len(page.text), size - overlap):
        end = min(start + size, len(page.text))
        if page.text[start:end].strip():
            chunks.append(_chunk(page, start, end))
        if end == len(page.text):
            break
    return chunks


def by_paragraph(page: DocumentPage, max_size: int) -> list[Chunk]:
    """Pack adjacent paragraphs, starting a new chunk at each AsciiDoc heading."""
    if max_size <= 0:
        raise ValueError("maximum chunk size must be positive")
    text = page.text
    boundaries = {match.end() for match in re.finditer(r"\n{2,}", text)}
    headings = {match.start() for match in re.finditer(r"^={2,} ", text, re.MULTILINE)}
    boundaries.update(headings)
    boundaries.add(len(text))

    chunks = []
    start = previous = 0
    for end in sorted(boundaries):
        if end - start > max_size and previous > start:
            if text[start:previous].strip():
                chunks.append(_chunk(page, start, previous))
            start = previous
        while end - start > max_size:
            limit = start + max_size
            space = max(text.rfind("\n", start, limit), text.rfind(" ", start, limit))
            stop = space + 1 if space >= start + max_size // 2 else limit
            if text[start:stop].strip():
                chunks.append(_chunk(page, start, stop))
            start = stop
        if end in headings or end == len(text):
            if text[start:end].strip():
                chunks.append(_chunk(page, start, end))
            start = end
        previous = end
    return chunks
