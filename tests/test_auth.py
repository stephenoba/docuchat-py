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
    data = response.json()["data"]
    assert data["email"] == "testauth@example.com"
    assert "id" in data

@pytest.mark.asyncio
async def test_register_user_duplicate(client: AsyncClient):
    payload = {
        "email": "duplicate@example.com",
        "password": "Password123!"
    }
    await client.post("/api/v1/auth/register", json=payload)
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "User with this email already exists"

@pytest.mark.asyncio
async def test_token_success(client: AsyncClient):
    # Register first
    payload = {
        "email": "logintest@example.com",
        "password": "Password123!"
    }
    await client.post("/api/v1/auth/register", json=payload)
    
    # Login payload is normally form-encoded for OAuth2 or simple JSON in this codebase
    login_params = {
        "email": "logintest@example.com",
        "password": "Password123!"
    }
    response = await client.post("/api/v1/auth/token", params=login_params)
    assert response.status_code == 200
    data = response.json()["data"]
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "Bearer"

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
    assert response.json()["detail"] == "Invalid username or password"

@pytest.mark.asyncio
async def test_token_user_not_found(client: AsyncClient):
    login_params = {
        "email": "notfound@example.com",
        "password": "Password123!"
    }
    response = await client.post("/api/v1/auth/token", params=login_params)
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"

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
    data = refresh_response.json()["data"]
    assert "access_token" in data
    assert "refresh_token" in data

@pytest.mark.asyncio
async def test_refresh_token_invalid(client: AsyncClient):
    refresh_response = await client.post("/api/v1/auth/refresh", params={"token": "invalid_format_token"})
    assert refresh_response.status_code == 401

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
    assert logout_response.json()["message"] == "User logged out successfully"

    # Try to reuse the token for refresh
    refresh_response = await client.post("/api/v1/auth/refresh", params={"token": refresh_token})
    assert refresh_response.status_code == 401
    assert "revoked" in refresh_response.json()["detail"].lower()
