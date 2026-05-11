import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"
    
    # Check for security headers
    assert "X-Frame-Options" in response.headers
    assert "X-Content-Type-Options" in response.headers
    assert "Strict-Transport-Security" in response.headers
    assert "Referrer-Policy" in response.headers

