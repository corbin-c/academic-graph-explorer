import os

# Set in-memory SQLite BEFORE any app imports
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

import pytest
from httpx import ASGITransport, AsyncClient

from app.cache.database import engine
from app.cache.models import Base
from app.main import app


@pytest.fixture(autouse=True)
async def _initialize_database():
    """Reset and recreate DB tables for each test (ASGITransport bypasses lifespan)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture
async def async_client():
    """Async HTTP client pointed at the FastAPI app with in-memory SQLite."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
