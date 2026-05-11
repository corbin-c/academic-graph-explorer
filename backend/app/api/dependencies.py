"""Shared FastAPI dependencies for all API routers."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.database import get_session
from app.sources.idref.sparql import IdRefSparqlClient


async def get_idref_client(
    session: AsyncSession = Depends(get_session),
) -> IdRefSparqlClient:
    """Provide an IdRef SPARQL client with cache session injected."""
    return IdRefSparqlClient(cache_session=session)
