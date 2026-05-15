import pytest
import json
from uuid import uuid4
from unittest.mock import patch, MagicMock
from app.events.event_handlers import handle_doc_events
from app.models import UsageLog
from app.core.config import DOCUMENT_EVENTS

@pytest.mark.asyncio
async def test_handle_doc_processed_event():
    user_id = uuid4()
    doc_id = uuid4()
    correlation_id = uuid4()
    
    payload = {
        "user_id": user_id,
        "document_id": str(doc_id),
        "correlation_id": str(correlation_id),
        "chunk_count": 5,
        "duration_ms": 100,
        "format": "txt",
        "page_count": 1,
        "tokens": 100,
        "cost": 0.01,
        "status": "success"
    }
    
    event = (DOCUMENT_EVENTS.PROCESSED.value, payload)
    
    # We need to mock the session and the metric
    with patch("app.events.event_handlers.async_session") as mock_session_cm, \
         patch("app.events.event_handlers.DOCUMENTS_PROCESSED") as mock_metric, \
         patch("app.models.UsageLog.objects.create") as mock_create:
        
        # Setup mock session
        mock_session = MagicMock()
        mock_session_cm.return_value.__aenter__.return_value = mock_session
        
        await handle_doc_events(event)
        
        # 1. Verify metric increment
        mock_metric.labels.assert_called_with(status="success")
        mock_metric.labels.return_value.inc.assert_called_once()
        
        # 2. Verify UsageLog creation
        # Note: action becomes "doc_processed" because event_name.split(":")[-1]
        mock_create.assert_called_once()
        args, kwargs = mock_create.call_args
        assert kwargs["user_id"] == user_id
        assert kwargs["action"] == "doc_processed"
        assert kwargs["tokens"] == 100
        assert kwargs["cost_usd"] == 0.01
        
        # Verify metadata
        metadata = json.loads(kwargs["log_metadata"])
        assert metadata["document_id"] == str(doc_id)
        assert metadata["chunk_count"] == 5

@pytest.mark.asyncio
async def test_handle_doc_processed_event_failure():
    user_id = uuid4()
    correlation_id = uuid4()
    
    payload = {
        "user_id": user_id,
        "correlation_id": str(correlation_id),
        "status": "failed",
        "error": "Some error"
    }
    
    event = (DOCUMENT_EVENTS.PROCESSED.value, payload)
    
    with patch("app.events.event_handlers.async_session") as mock_session_cm, \
         patch("app.events.event_handlers.DOCUMENTS_PROCESSED") as mock_metric, \
         patch("app.models.UsageLog.objects.create") as mock_create:
        
        mock_session = MagicMock()
        mock_session_cm.return_value.__aenter__.return_value = mock_session
        
        await handle_doc_events(event)
        
        # 1. Verify metric increment with status="failed"
        mock_metric.labels.assert_called_with(status="failed")
        mock_metric.labels.return_value.inc.assert_called_once()
