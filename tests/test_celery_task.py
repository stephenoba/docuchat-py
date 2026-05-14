from unittest.mock import patch, MagicMock
from uuid import uuid4

from app.queues.celery_task import process_document
from app.models.models import Document, DocumentStatus

@patch("app.queues.celery_task.dispatch")
@patch("app.queues.celery_task.SessionLocal")
@patch("app.queues.celery_task.asyncio.run")
@patch("app.queues.celery_task.split_document")
def test_process_document_success(mock_split, mock_async_run, mock_session_local, mock_dispatch):
    # 1. Setup IDs
    user_id = uuid4()
    doc_id = uuid4()
    correlation_id = uuid4()
    
    # 2. Mock Database Session
    mock_session = MagicMock()
    mock_session_local.return_value.__enter__.return_value = mock_session
    
    # Mock the document object
    mock_doc = MagicMock(spec=Document)
    mock_doc.id = doc_id
    mock_doc.content = b"Hello world"
    mock_doc.filename = "test.txt"
    mock_doc.status = DocumentStatus.PENDING.value
    mock_session.get.return_value = mock_doc
    
    # 3. Setup Logic Mocks
    mock_split.return_value = [
        {"content": "Hello", "token_count": 1, "index": 0, "metadata": {"start_char": 0, "end_char": 5}},
        {"content": "world", "token_count": 1, "index": 1, "metadata": {"start_char": 6, "end_char": 11}}
    ]
    
    # asyncio.run(generate_embeddings_batch_cached(...)) returns the embeddings
    mock_async_run.return_value = [
        [0.1, 0.1], 
        [0.2, 0.2]
    ]
    
    # 4. Mock the celery task 'self' properly
    mock_self = MagicMock()
    mock_self.request.id = "test-task-id"
    mock_self.request.retries = 0
    mock_self.max_retries = 3
    
    # 5. Execute task
    process_document.__wrapped__.__func__(mock_self, str(doc_id), str(user_id), str(correlation_id))
    
    # 6. Verify results
    mock_session.get.assert_called_once()
    assert mock_async_run.call_count >= 2
    
    # Check chunks added
    args, _ = mock_session.add_all.call_args
    chunks_added = args[0]
    assert len(chunks_added) == 2
    
    assert mock_doc.status == DocumentStatus.READY.value
    # Expect 3 commits: one for status=PROCESSING, one for chunks, one for final result
    assert mock_session.commit.call_count == 3
