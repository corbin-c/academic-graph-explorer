"""
IdRef SPARQL queries.

IdRef (Identifiants et Référentiels) is the French national authority
file for higher education and research, maintained by ABES.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.sources.client import HttpSparqlClient

IDREF_ENDPOINT = "https://data.idref.fr/sparql"


class IdRefSparqlClient(HttpSparqlClient):
    """SPARQL client for the IdRef endpoint with optional response caching."""

    def __init__(self, cache_session: AsyncSession | None = None):
        super().__init__(IDREF_ENDPOINT)
        self.cache_session = cache_session

    async def cached_query(
        self, sparql: str, cache_session: AsyncSession | None = None, ttl: int = 3600
    ) -> dict:
        """Run a cached SPARQL query against IdRef.

        Uses the cache_session provided at construction by default.
        Results are cached for ttl seconds when a session is available.
        """
        session = cache_session if cache_session is not None else self.cache_session
        return await super().cached_query(sparql, session, ttl)
