import os
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport

# Set testing overrides before any other imports that might instantiate the engine
# Set testing overrides only if not already set (e.g. by Docker)
TEST_DB_PATH = Path("test_db.sqlite3")
db_url = os.environ.get("DATABASE_URL", f"sqlite:///{TEST_DB_PATH}")

# If using Postgres, switch to the test database
if "postgresql" in db_url or "postgres" in db_url:
    if "/docuchat" in db_url and "/docuchat_test" not in db_url:
        db_url = db_url.replace("/docuchat", "/docuchat_test")

os.environ["DATABASE_URL"] = db_url
os.environ.setdefault("SECRET_KEY", "testsecret")
os.environ.setdefault("REFRESH_SECRET_KEY", "testrefreshsecret")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

# We must import after environment configs are overridden
from app.main import app  # noqa: E402
from app.models.dbmanager import async_engine, SQLModel  # noqa: E402
from scripts.seed_db import seed_rbac  # noqa: E402
from app.extensions.redis import redis_client  # noqa: E402



@pytest.fixture(autouse=True)
async def setup_db():
    # For Postgres, we want to ensure we start fresh but also handle connections safely
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
    
    # Seed RBAC for tests
    await seed_rbac()
    yield
    # No need to drop here as we do it at the start of next test
    # but we DO need to dispose of the engine to avoid loop mismatch errors
    await async_engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db():
    """Remove the test database file after the entire test session (for SQLite)."""
    yield
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


@pytest.fixture(autouse=True)
async def clear_redis():
    """Flush redis and disconnect connection pool between tests to avoid loop mismatch."""
    try:
        await redis_client.flushdb()
    except Exception:
        pass
    yield
    try:
        await redis_client.aclose()
    except Exception:
        pass



@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
