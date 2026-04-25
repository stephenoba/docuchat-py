import pytest
from httpx import AsyncClient


async def get_auth_headers(client: AsyncClient, email: str = "conv_test@example.com"):
    payload = {"email": email, "password": "Password123!"}
    await client.post("/api/v1/auth/register", json=payload)

    login_params = {"email": email, "password": "Password123!"}
    token_response = await client.post("/api/v1/auth/token", params=login_params)
    access_token = token_response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


@pytest.mark.asyncio
async def test_create_conversation_success(client: AsyncClient):
    headers = await get_auth_headers(client)
    payload = {"title": "Test Chat"}
    response = await client.post("/api/v1/conversation", json=payload, headers=headers)
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["title"] == "Test Chat"


@pytest.mark.asyncio
async def test_list_conversations_success(client: AsyncClient):
    headers = await get_auth_headers(client, email="conv_list@example.com")
    await client.post("/api/v1/conversation", json={"title": "Chat 1"}, headers=headers)
    await client.post("/api/v1/conversation", json={"title": "Chat 2"}, headers=headers)

    response = await client.get("/api/v1/conversation", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]) == 3  # 1 welcome + 2 created


@pytest.mark.asyncio
async def test_get_conversation_success(client: AsyncClient):
    headers = await get_auth_headers(client, email="conv_get@example.com")
    create_resp = await client.post(
        "/api/v1/conversation", json={"title": "Target Chat"}, headers=headers
    )
    conv_id = create_resp.json()["data"]["id"]

    response = await client.get(f"/api/v1/conversation/{conv_id}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["title"] == "Target Chat"


@pytest.mark.asyncio
async def test_update_conversation_success(client: AsyncClient):
    headers = await get_auth_headers(client, email="conv_update@example.com")
    create_resp = await client.post(
        "/api/v1/conversation", json={"title": "Old Chat"}, headers=headers
    )
    conv_id = create_resp.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/conversation/{conv_id}", json={"title": "New Chat"}, headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["title"] == "New Chat"


@pytest.mark.asyncio
async def test_delete_conversation_hard(client: AsyncClient):
    headers = await get_auth_headers(client, email="conv_delete@example.com")
    create_resp = await client.post(
        "/api/v1/conversation", json={"title": "To Delete"}, headers=headers
    )
    conv_id = create_resp.json()["data"]["id"]

    # Delete
    del_resp = await client.delete(f"/api/v1/conversation/{conv_id}", headers=headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True

    # Verify it's gone
    get_resp = await client.get(f"/api/v1/conversation/{conv_id}", headers=headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_unauthorized_conversation_access(client: AsyncClient):
    response = await client.get("/api/v1/conversation")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_send_message_success(client: AsyncClient):
    headers = await get_auth_headers(client, email="send@example.com")
    # First create a conversation
    create_resp = await client.post(
        "/api/v1/conversation", json={"title": "Chat"}, headers=headers
    )
    assert create_resp.status_code == 201
    conv_id = create_resp.json()["data"]["id"]

    # Send message to that conversation
    msg_resp = await client.post(
        f"/api/v1/conversation/{conv_id}/messages",
        json={"content": "Hello world from test"},
        headers=headers,
    )
    assert msg_resp.status_code == 201
    body = msg_resp.json()
    assert body["data"]["content"] == "Hello world from test"
    assert body["data"]["role"] == "user"
    assert body["data"]["conversation_id"] == conv_id
