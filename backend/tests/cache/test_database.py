import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.database import create_db_and_tables, get_session


class TestDatabase:
    @pytest.mark.asyncio
    async def test_create_db_and_tables_does_not_raise(self):
        # Should succeed without errors (tables may already exist, checkfirst=True)
        await create_db_and_tables()

    @pytest.mark.asyncio
    async def test_get_session_yields_async_session(self):
        async for session in get_session():
            assert isinstance(session, AsyncSession)


class TestDatabaseEngine:
    @pytest.mark.asyncio
    async def test_engine_uses_in_memory_sqlite(self):
        from app.cache.database import engine

        url = str(engine.url)
        assert ":memory:" in url or url == "sqlite+aiosqlite://"
