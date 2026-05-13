from app.core.utils import split_document

def test_split_document_basic():
    content = "This is a test document that should be split into multiple chunks."
    # With a very small chunk size, it should split
    chunks = split_document(content, chunk_size=5, chunk_overlap=0)
    assert len(chunks) > 1
    assert all("content" in c and "token_count" in c for c in chunks)
    assert "".join([c["content"] for c in chunks]) == content

def test_split_document_overlap():
    content = "One two three four five six seven eight nine ten"
    chunk_size = 5
    chunk_overlap = 2
    chunks = split_document(content, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    
    # Check that chunks exist
    assert len(chunks) > 1
    
    # Verify that there is some overlap in content between consecutive chunks
    # (Note: exact character overlap varies with tokenization, but semantic overlap should exist)
    for i in range(len(chunks) - 1):
        assert any(word in chunks[i+1]["content"] for word in chunks[i]["content"].split())

def test_split_document_empty():
    assert split_document("") == []

def test_split_document_small():
    content = "Short text"
    chunks = split_document(content, chunk_size=100, chunk_overlap=10)
    assert len(chunks) == 1
    assert chunks[0]["content"] == content
    assert chunks[0]["token_count"] > 0
