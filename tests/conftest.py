import os
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport

# Set testing overrides before any other imports that might instantiate the engine
TEST_DB_PATH = Path("test_db.sqlite3")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH}"
os.environ["SECRET_KEY"] = "testsecret"
os.environ["REFRESH_SECRET_KEY"] = "testrefreshsecret"
os.environ["DEBUG"] = "false"

# We must import after environment configs are overridden
from main import app  # noqa: E402
from dbmanager import engine, SQLModel  # noqa: E402


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db():
    """Remove the test database file after the entire test session."""
    yield
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
