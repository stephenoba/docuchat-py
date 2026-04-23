import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_register_user_success(client: AsyncClient):
    payload = {
        "email": "testauth@example.com",
        "password": "Password123!"
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["email"] == "testauth@example.com"
    assert "id" in body["data"]

@pytest.mark.asyncio
async def test_register_user_duplicate(client: AsyncClient):
    payload = {
        "email": "duplicate@example.com",
        "password": "Password123!"
    }
    await client.post("/api/v1/auth/register", json=payload)
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "USER_ALREADY_EXISTS"

@pytest.mark.asyncio
async def test_token_success(client: AsyncClient):
    payload = {
        "email": "logintest@example.com",
        "password": "Password123!"
    }
    await client.post("/api/v1/auth/register", json=payload)
    
    login_params = {
        "email": "logintest@example.com",
        "password": "Password123!"
    }
    response = await client.post("/api/v1/auth/token", params=login_params)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "access_token" in body["data"]
    assert "refresh_token" in body["data"]
    assert body["data"]["token_type"] == "Bearer"

@pytest.mark.asyncio
async def test_token_invalid_password(client: AsyncClient):
    payload = {
        "email": "badpass@example.com",
        "password": "Password123!"
    }
    await client.post("/api/v1/auth/register", json=payload)
    
    login_params = {
        "email": "badpass@example.com",
        "password": "WrongPassword"
    }
    response = await client.post("/api/v1/auth/token", params=login_params)
    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_PASSWORD"

@pytest.mark.asyncio
async def test_token_user_not_found(client: AsyncClient):
    login_params = {
        "email": "notfound@example.com",
        "password": "Password123!"
    }
    response = await client.post("/api/v1/auth/token", params=login_params)
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "USER_NOT_FOUND"

@pytest.mark.asyncio
async def test_refresh_token_success(client: AsyncClient):
    payload = {
        "email": "refresh@example.com",
        "password": "Password123!"
    }
    await client.post("/api/v1/auth/register", json=payload)
    
    login_params = {
        "email": "refresh@example.com",
        "password": "Password123!"
    }
    response = await client.post("/api/v1/auth/token", params=login_params)
    refresh_token = response.json()["data"]["refresh_token"]

    refresh_response = await client.post("/api/v1/auth/refresh", params={"token": refresh_token})
    assert refresh_response.status_code == 200
    body = refresh_response.json()
    assert body["success"] is True
    assert "access_token" in body["data"]
    assert "refresh_token" in body["data"]

@pytest.mark.asyncio
async def test_refresh_token_invalid(client: AsyncClient):
    refresh_response = await client.post("/api/v1/auth/refresh", params={"token": "invalid_format_token"})
    assert refresh_response.status_code == 401
    body = refresh_response.json()
    assert body["success"] is False

@pytest.mark.asyncio
async def test_logout_success(client: AsyncClient):
    payload = {
        "email": "logout@example.com",
        "password": "Password123!"
    }
    await client.post("/api/v1/auth/register", json=payload)
    
    login_params = {
        "email": "logout@example.com",
        "password": "Password123!"
    }
    response = await client.post("/api/v1/auth/token", params=login_params)
    refresh_token = response.json()["data"]["refresh_token"]

    logout_response = await client.post("/api/v1/auth/logout", params={"token": refresh_token})
    assert logout_response.status_code == 200
    body = logout_response.json()
    assert body["success"] is True
    assert body["message"] == "User logged out successfully"

    # Try to reuse the token for refresh
    refresh_response = await client.post("/api/v1/auth/refresh", params={"token": refresh_token})
    assert refresh_response.status_code == 401
    body = refresh_response.json()
    assert body["success"] is False
