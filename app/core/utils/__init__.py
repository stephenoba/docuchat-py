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


def safe_dispatch(event: str, payload: dict):
    """
    Dispatch an event safely, ignoring LookupError which occurs when
    dispatched outside of a FastAPI request context (e.g. in Celery).
    """
    try:
        from fastapi_events.dispatcher import dispatch
        dispatch(event, payload)
    except LookupError:
        # FastAPI-events requires a request context to find the event handler.
        # In background tasks, we just skip it or log it.
        pass
