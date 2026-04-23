import os
import asyncio
import pytest
from httpx import AsyncClient, ASGITransport

# Set testing overrides before any other imports that might instantiate the engine
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test_db.sqlite3"
os.environ["SECRET_KEY"] = "testsecret"
os.environ["REFRESH_SECRET_KEY"] = "testrefreshsecret"

# We must import after environment configs are overridden
from main import app
from dbmanager import engine, SQLModel

@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)

@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
