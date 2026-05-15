import pytest
from uuid import uuid4
from unittest.mock import patch, AsyncMock, MagicMock
from app.services.rag import assemble_context, CONTEXT_TOKEN_BUDGET, generate_rag_response, AssembledContext
from app.schemas.document import SearchResult


@pytest.mark.asyncio
async def test_generate_rag_response_success():
    doc_id = uuid4()
    context = AssembledContext(
        chunks=[
            SearchResult(
                chunk_id=uuid4(),
                document_id=doc_id,
                document_title="Doc 1",
                content="Chunk 0",
                chunk_index=0,
                score=0.9,
                token_count=100
            )
        ],
        context_text="[Source 1: \"Doc 1\", Section 1]\nChunk 0",
        total_tokens=100,
        citations=[]
    )
    
    # Mock response
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "The answer is 42"}}],
        "usage": {
            "prompt_tokens": 150,
            "completion_tokens": 50,
            "total_tokens": 200
        }
    }
    
    with patch("app.services.rag.openai_request", new_callable=AsyncMock) as mock_request, \
         patch("app.services.rag.safe_dispatch") as mock_dispatch:
        
        mock_request.return_value = mock_resp
        
        response = await generate_rag_response(
            question="What is the answer?",
            context=context,
            user_id=str(uuid4()),
            conversation_id=str(uuid4()),
            correlation_id="test-corr-id"
        )
        
        assert response.answer == "The answer is 42"
        assert response.tokens_used.total == 200
        assert mock_request.called
        assert mock_dispatch.called


def test_assemble_context_within_budget():
    doc_id = uuid4()
    results = [
        SearchResult(
            chunk_id=uuid4(),
            document_id=doc_id,
            document_title="Doc 1",
            content="Content 1",
            chunk_index=0,
            score=0.9,
            token_count=100
        ),
        SearchResult(
            chunk_id=uuid4(),
            document_id=doc_id,
            document_title="Doc 1",
            content="Content 2",
            chunk_index=5,
            score=0.8,
            token_count=200
        )
    ]
    
    assembled = assemble_context(results)
    
    assert len(assembled.chunks) == 2
    assert assembled.total_tokens == 300
    assert len(assembled.citations) == 2
    assert "[Source 1: \"Doc 1\", Section 1]" in assembled.context_text
    assert "[Source 2: \"Doc 1\", Section 6]" in assembled.context_text
    assert "Content 1" in assembled.context_text
    assert "Content 2" in assembled.context_text
    assert "---" in assembled.context_text


def test_assemble_context_exceeds_budget():
    doc_id = uuid4()
    # Create results that will exceed the budget
    results = [
        SearchResult(
            chunk_id=uuid4(),
            document_id=doc_id,
            document_title="Doc 1",
            content="Large Content",
            chunk_index=0,
            score=0.9,
            token_count=CONTEXT_TOKEN_BUDGET - 100
        ),
        SearchResult(
            chunk_id=uuid4(),
            document_id=doc_id,
            document_title="Doc 2",
            content="Will not fit",
            chunk_index=0,
            score=0.8,
            token_count=200
        )
    ]
    
    assembled = assemble_context(results)
    
    # Only the first one should be included
    assert len(assembled.chunks) == 1
    assert assembled.total_tokens == CONTEXT_TOKEN_BUDGET - 100
    assert assembled.chunks[0].document_title == "Doc 1"
    assert "Doc 2" not in assembled.context_text


def test_assemble_context_empty_results():
    assembled = assemble_context([])
    
    assert len(assembled.chunks) == 0
    assert assembled.total_tokens == 0
    assert assembled.context_text == ""
    assert len(assembled.citations) == 0


def test_assemble_context_deduplication():
    doc_id = uuid4()
    results = [
        SearchResult(
            chunk_id=uuid4(),
            document_id=doc_id,
            document_title="Doc 1",
            content="Chunk 0",
            chunk_index=0,
            score=0.9,
            token_count=100
        ),
        SearchResult(
            chunk_id=uuid4(),
            document_id=doc_id,
            document_title="Doc 1",
            content="Chunk 1 (Adjacent)",
            chunk_index=1,
            score=0.85,
            token_count=100
        ),
        SearchResult(
            chunk_id=uuid4(),
            document_id=doc_id,
            document_title="Doc 1",
            content="Chunk 5 (Not Adjacent)",
            chunk_index=5,
            score=0.8,
            token_count=100
        )
    ]
    
    assembled = assemble_context(results)
    
    # Should include Chunk 0 and Chunk 5, but skip Chunk 1 because it's adjacent to Chunk 0
    assert len(assembled.chunks) == 2
    assert assembled.chunks[0].chunk_index == 0
    assert assembled.chunks[1].chunk_index == 5
    assert "Chunk 1" not in assembled.context_text
