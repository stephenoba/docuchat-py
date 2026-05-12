import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check_live(client: AsyncClient):
    response = await client.get("/health/live")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"
    
    # Verify that security headers are EXEMPT for health endpoints
    assert "X-Frame-Options" not in response.headers
    assert "Strict-Transport-Security" not in response.headers


@pytest.mark.asyncio
async def test_health_check_ready(client: AsyncClient):
    response = await client.get("/health/ready")
    # ready check returns 200 if all services are up, 503 if some are down
    assert response.status_code in [200, 503]
    body = response.json()
    assert "checks" in body["data"]
    
    # Verify exemption
    assert "X-Frame-Options" not in response.headers

@pytest.mark.asyncio
async def test_security_headers_on_api(client: AsyncClient):
    # Any non-health endpoint should have headers
    response = await client.get("/api/v1/auth/login") # Just a path check
    assert "X-Frame-Options" in response.headers
    assert "Strict-Transport-Security" in response.headers



