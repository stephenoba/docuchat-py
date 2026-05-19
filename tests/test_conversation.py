import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock, MagicMock

from app.schemas.conversation import RAGResponse, TokenUsage


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
    assert body["meta"]["total"] == 3
    assert body["meta"]["page"] == 1


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

    # Mock RAG dependencies
    mock_rag_resp = RAGResponse(
        answer="I am an AI assistant",
        citations=[],
        tokens_used=TokenUsage(prompt=10, completion=10, total=20),
        cost_usd=0.0001,
        model="gpt-4o"
    )

    with patch("app.services.conversation.semantic_search", new_callable=AsyncMock) as mock_search, \
         patch("app.services.conversation.generate_rag_response", new_callable=AsyncMock) as mock_rag, \
         patch("app.services.conversation.assemble_context") as mock_assemble:
        
        mock_search.return_value = []
        mock_assemble_val = MagicMock()
        mock_assemble_val.chunks = []
        mock_assemble_val.citations = []
        mock_assemble.return_value = mock_assemble_val
        mock_rag.return_value = mock_rag_resp

        # Send message to that conversation
        msg_resp = await client.post(
            f"/api/v1/conversation/{conv_id}/messages",
            json={"content": "Hello world from test"},
            headers=headers,
        )
        assert msg_resp.status_code == 201
        body = msg_resp.json()
        
        assert "user_message" in body["data"]
        assert "assistant_message" in body["data"]
        assert body["data"]["user_message"]["content"] == "Hello world from test"
        assert body["data"]["assistant_message"]["content"] == "I am an AI assistant"
        assert body["data"]["user_message"]["conversation_id"] == conv_id
