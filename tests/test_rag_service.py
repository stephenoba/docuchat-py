import pytest
from uuid import uuid4
from app.services.rag import assemble_context, CONTEXT_TOKEN_BUDGET
from app.schemas.document import SearchResult


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
