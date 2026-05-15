import pytest
from unittest.mock import patch, MagicMock
from app.services.embedding import (
    generate_embeddings, 
    generate_embedding_cached, 
    generate_embeddings_batch_cached,
    content_hash
)

@pytest.mark.asyncio
@patch("app.services.embedding.openai_request")
@patch("app.services.embedding.safe_dispatch")
async def test_generate_embeddings(mock_safe_dispatch, mock_openai_request):
    # Mock AI response - Use MagicMock for the response itself 
    # because response.json() is a sync method.
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {"index": 0, "embedding": [0.1, 0.2, 0.3]},
            {"index": 1, "embedding": [0.4, 0.5, 0.6]}
        ],
        "usage": {"total_tokens": 10}
    }
    mock_openai_request.return_value = mock_response
    
    texts = ["text1", "text2"]
    embeddings = await generate_embeddings(texts)
    
    assert len(embeddings) == 2
    assert embeddings[0] == [0.1, 0.2, 0.3]
    assert embeddings[1] == [0.4, 0.5, 0.6]
    assert mock_safe_dispatch.called

@pytest.mark.asyncio
@patch("app.services.embedding.cache_get")
@patch("app.services.embedding.cache_set")
@patch("app.services.embedding.generate_embeddings")
async def test_generate_embedding_cached_miss(mock_gen, mock_set, mock_get):
    mock_get.return_value = None
    mock_gen.return_value = [[0.1, 0.2, 0.3]]
    
    text = "new text"
    embedding = await generate_embedding_cached(text)
    
    assert embedding == [0.1, 0.2, 0.3]
    assert mock_gen.called
    assert mock_set.called

@pytest.mark.asyncio
@patch("app.services.embedding.cache_get")
@patch("app.services.embedding.cache_set")
@patch("app.services.embedding.generate_embeddings")
async def test_generate_embedding_cached_hit(mock_gen, mock_set, mock_get):
    mock_get.return_value = [0.1, 0.2, 0.3]
    
    text = "cached text"
    embedding = await generate_embedding_cached(text)
    
    assert embedding == [0.1, 0.2, 0.3]
    assert not mock_gen.called
    assert not mock_set.called

@pytest.mark.asyncio
@patch("app.services.embedding.cache_get")
@patch("app.services.embedding.cache_set")
@patch("app.services.embedding.generate_embeddings")
async def test_generate_embeddings_batch_cached(mock_gen, mock_set, mock_get):
    # Mock behavior: first text is cached, second is not
    h1 = content_hash("text1")
    
    async def mock_get_side_effect(key):
        if h1 in key:
            return [0.1, 0.1, 0.1]
        return None
    
    mock_get.side_effect = mock_get_side_effect
    mock_gen.return_value = [[0.2, 0.2, 0.2]]
    
    texts = ["text1", "text2"]
    results = await generate_embeddings_batch_cached(texts)
    
    assert len(results) == 2
    assert results[0] == [0.1, 0.1, 0.1]
    assert results[1] == [0.2, 0.2, 0.2]
    
    # Verify generate_embeddings was only called for the second text
    mock_gen.assert_called_once_with(["text2"], None, None)
    assert mock_set.called
