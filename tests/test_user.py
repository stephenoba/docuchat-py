import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_me_unauthorized(client: AsyncClient):
    response = await client.get("/api/v1/user/me")
    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False

@pytest.mark.asyncio
async def test_get_me_success(client: AsyncClient):
    # Register and get token
    payload = {
        "email": "user_me@example.com",
        "password": "Password123!"
    }
    await client.post("/api/v1/auth/register", json=payload)
    
    login_params = {
        "email": "user_me@example.com",
        "password": "Password123!"
    }
    token_response = await client.post("/api/v1/auth/token", params=login_params)
    access_token = token_response.json()["data"]["access_token"]
    
    # Request /me
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await client.get("/api/v1/user/me", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["email"] == "user_me@example.com"
    assert "id" in body["data"]
    assert "tier" in body["data"]
