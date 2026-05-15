import pytest
import uuid
from httpx import AsyncClient
from sqlmodel import select
from unittest.mock import patch, AsyncMock
from app.dependencies.rate_limiter import auth_limiter, general_limiter, chat_limiter
from app.auth import create_access_token
from app.models import User, Role, UserRole, Conversation, Message
from app.models.dbmanager import async_session
from app.core.utils import utcnow

@pytest.mark.asyncio
async def test_auth_rate_limit(client: AsyncClient):
    # Mock auth limit to 2
    orig_auth = auth_limiter.requests
    auth_limiter.requests = 2
    try:
        # Request 1: OK
        resp1 = await client.post("/api/v1/auth/register", json={"email": "rate1@example.com", "password": "Password123!"})
        assert resp1.status_code == 201
        assert resp1.headers["RateLimit-Remaining"] == "1"
        
        # Request 2: OK
        resp2 = await client.post("/api/v1/auth/register", json={"email": "rate2@example.com", "password": "Password123!"})
        assert resp2.status_code == 201
        assert resp2.headers["RateLimit-Remaining"] == "0"
        
        # Request 3: 429
        resp3 = await client.post("/api/v1/auth/register", json={"email": "rate3@example.com", "password": "Password123!"})
        assert resp3.status_code == 429
        assert resp3.headers["RateLimit-Limit"] == "2"
    finally:
        auth_limiter.requests = orig_auth

@pytest.mark.asyncio
async def test_tiered_rate_limit_pro_tier(client: AsyncClient):
    # Mock pro tier limit to 2
    orig_gen = general_limiter.tiered_limits.copy()
    general_limiter.tiered_limits["pro"] = (2, 60000)
    try:
        user_id = uuid.uuid4()
        async with async_session() as session:
            async with session.begin():
                user = User(id=user_id, email="pro@example.com", username="pro@example.com", tier="pro", password_hash="hash")
                session.add(user)
                role = (await session.execute(select(Role).where(Role.name == "member"))).scalars().first()
                if role:
                    session.add(UserRole(user_id=user_id, role_id=role.id))
        
        token = create_access_token(user)
        headers = {"Authorization": f"Bearer {token}"}
        
        for i in range(2):
            resp = await client.get("/api/v1/user/me", headers=headers)
            assert resp.status_code == 200
            assert int(resp.headers["RateLimit-Remaining"]) == 1 - i
            
        resp_429 = await client.get("/api/v1/user/me", headers=headers)
        assert resp_429.status_code == 429
    finally:
        general_limiter.tiered_limits = orig_gen

@pytest.mark.asyncio
async def test_chat_rate_limit_enterprise(client: AsyncClient):
    # Mock enterprise tier limit to 2 for chat
    orig_chat = chat_limiter.tiered_limits.copy()
    chat_limiter.tiered_limits["enterprise"] = (2, 60000)
    try:
        user_id = uuid.uuid4()
        conv_id = uuid.uuid4()
        async with async_session() as session:
            async with session.begin():
                user = User(id=user_id, email="ent@example.com", username="ent@example.com", tier="enterprise", password_hash="hash")
                session.add(user)
                role = (await session.execute(select(Role).where(Role.name == "member"))).scalars().first()
                if role:
                    session.add(UserRole(user_id=user_id, role_id=role.id))
                
                conv = Conversation(id=conv_id, user_id=user_id, title="Test")
                session.add(conv)
        
        token = create_access_token(user)
        headers = {"Authorization": f"Bearer {token}"}
        url = f"/api/v1/conversation/{conv_id}/messages"
        
        mock_result = {
            "user_message": Message(id=uuid.uuid4(), conversation_id=conv_id, role="user", content="hi", created_at=utcnow()),
            "assistant_message": Message(id=uuid.uuid4(), conversation_id=conv_id, role="assistant", content="AI response", created_at=utcnow()),
            "citations": []
        }

        with patch("app.routers.v1.conversation.send_message_service", new_callable=AsyncMock) as mock_service:
            mock_service.return_value = mock_result
            
            for i in range(2):
                resp = await client.post(url, json={"content": "hi"}, headers=headers)
                assert resp.status_code == 201
                assert "RateLimit-Remaining" in resp.headers
                
            resp_429 = await client.post(url, json={"content": "hi"}, headers=headers)
            assert resp_429.status_code == 429
    finally:
        chat_limiter.tiered_limits = orig_chat
