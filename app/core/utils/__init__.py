from datetime import datetime, timezone
from .document_extractor import (
    detect_format, # noqa: F401
    clean_extracted_text, # noqa: F401
    extract_text # noqa: F401
)
from .chunker import split_document # noqa: F401

def utcnow() -> datetime:
    """Return a naive UTC datetime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
