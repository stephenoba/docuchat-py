import pytest
from httpx import AsyncClient
from app.extensions.cache_service import cache_get, cache_set


@pytest.mark.asyncio
async def test_metrics_middleware_increments_counter(client: AsyncClient):
    # Get initial count
    # Note: metrics are global, so we might need to handle that in tests
    # But for a simple test, we just check if it's present and increments
    
    response = await client.get("/health/live")
    assert response.status_code == 200
    
    metrics_response = await client.get("/metrics")
    assert response.status_code == 200
    assert 'docuchat_http_requests_total{method="GET",path="/health/live",status_code="200"}' in metrics_response.text


@pytest.mark.asyncio
async def test_metrics_middleware_normalizes_path(client: AsyncClient):
    # Test UUID normalization
    uuid_path = "/api/v1/document/123e4567-e89b-12d3-a456-426614174000"
    # We don't need a real endpoint, just something that triggers the middleware
    # Even a 404 should be recorded with normalized path
    await client.get(uuid_path)
    
    metrics_response = await client.get("/metrics")
    assert 'path="/api/v1/document/:id"' in metrics_response.text

    # Test numeric normalization
    numeric_path = "/api/v1/user/123"
    await client.get(numeric_path)
    
    metrics_response = await client.get("/metrics")
    assert 'path="/api/v1/user/:num"' in metrics_response.text


@pytest.mark.asyncio
async def test_cache_metrics(client: AsyncClient):
    # Test cache set
    await cache_set("test_key", {"data": "value"}, ttl_seconds=60)
    
    metrics_response = await client.get("/metrics")
    assert 'docuchat_cache_operations_total{operation="set",result="success"}' in metrics_response.text
    
    # Test cache hit
    await cache_get("test_key")
    metrics_response = await client.get("/metrics")
    assert 'docuchat_cache_operations_total{operation="get",result="hit"}' in metrics_response.text
    
    # Test cache miss
    await cache_get("non_existent_key")
    metrics_response = await client.get("/metrics")
    assert 'docuchat_cache_operations_total{operation="get",result="miss"}' in metrics_response.text
