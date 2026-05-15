from unittest.mock import patch, MagicMock
from uuid import uuid4

from app.queues.celery_task import _process_document_impl
from app.models.models import Document, DocumentStatus

@patch("app.queues.celery_task.safe_dispatch")
@patch("app.queues.celery_task.SessionLocal")
@patch("app.queues.celery_task.generate_embeddings_batch_cached_sync")
@patch("app.queues.celery_task.split_document")
def test_process_document_success(mock_split, mock_gen_sync, mock_session_local, mock_safe_dispatch):
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
    
    # generate_embeddings_batch_cached_sync returns the embeddings
    mock_gen_sync.return_value = [
        [0.1, 0.1], 
        [0.2, 0.2]
    ]
    
    # 4. Mock the celery task 'self' properly
    mock_self = MagicMock()
    mock_self.request.id = "test-task-id"
    mock_self.request.retries = 0
    mock_self.max_retries = 3
    
    # 5. Execute task
    _process_document_impl(mock_self, str(doc_id), str(user_id), str(correlation_id))
    
    # 6. Verify results
    mock_session.get.assert_called_once()
    assert mock_gen_sync.called
    
    # Check chunks added
    args, _ = mock_session.add_all.call_args
    chunks_added = args[0]
    assert len(chunks_added) == 2
    
    assert mock_doc.status == DocumentStatus.READY.value
    # Expect 3 commits: one for status=PROCESSING, one for chunks, one for final result
    assert mock_session.commit.call_count == 3
