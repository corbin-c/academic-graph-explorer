"""
SPARQL client for querying external RDF data sources.
"""

import asyncio
import hashlib
import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Many endpoints return plain JSON rather than the stricter SPARQL results format.
# We accept both.
SPARQL_ACCEPT_HEADERS = "application/sparql-results+json, application/json;q=0.9"


class SparqlQueryError(Exception):
    """Raised when a SPARQL query to an external endpoint fails."""

    def __init__(self, endpoint: str, original_error: Exception):
        self.endpoint = endpoint
        self.original_error = original_error
        super().__init__(f"SPARQL query to {endpoint} failed: {original_error}")


class SparqlClient(ABC):
    """Abstract client for a SPARQL endpoint."""

    @abstractmethod
    async def query(self, sparql: str) -> dict:
        """Execute a SPARQL query and return results as JSON."""
        ...

    @abstractmethod
    async def cached_query(
        self, sparql: str, cache_session: AsyncSession | None = None, ttl: int = 3600
    ) -> dict:
        """Execute a SPARQL query with optional caching."""
        ...


class HttpSparqlClient(SparqlClient):
    """SPARQL client that communicates over HTTP with retry and optional caching."""

    def __init__(self, endpoint_url: str):
        self.endpoint_url = endpoint_url
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient()
        return self._client

    async def close(self):
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def query(self, sparql: str, max_retries: int = 3) -> dict:
        """Execute a SPARQL query with retry on transient errors."""
        last_error: Exception | None = None

        for attempt in range(max_retries):
            try:
                client = await self._get_client()
                response = await client.post(
                    self.endpoint_url,
                    data={"query": sparql},
                    headers={"Accept": SPARQL_ACCEPT_HEADERS},
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()
            except (
                httpx.TimeoutException,
                httpx.NetworkError,
                httpx.ConnectError,
            ) as e:
                last_error = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(2**attempt)
                    continue
                raise SparqlQueryError(self.endpoint_url, e) from e
            except httpx.HTTPStatusError as e:
                raise SparqlQueryError(self.endpoint_url, e) from e
            except json.JSONDecodeError as e:
                raise SparqlQueryError(self.endpoint_url, e) from e

        # Should not be reached, but satisfy type checker
        raise SparqlQueryError(self.endpoint_url, last_error or RuntimeError("unknown"))

    async def cached_query(
        self,
        sparql: str,
        cache_session: AsyncSession | None = None,
        ttl: int = 3600,
    ) -> dict:
        """Execute a SPARQL query, using cache if available."""
        if cache_session is None:
            return await self.query(sparql)

        from app.cache.models import CachedQuery

        source = self.endpoint_url
        query_hash = hashlib.sha256((source + "|" + sparql).encode("utf-8")).hexdigest()

        # Check cache
        result = await cache_session.execute(
            select(CachedQuery).where(CachedQuery.query_hash == query_hash)
        )
        cached = result.scalar_one_or_none()
        if cached is not None:
            cached_created = cached.created_at
            if cached_created.tzinfo is None:
                cached_created = cached_created.replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - cached_created).total_seconds()
            if age < cached.ttl_seconds:
                return json.loads(cached.response_json)

        # Cache miss — query live
        data = await self.query(sparql)

        # Persist to cache (upsert)
        if cached is not None:
            cached.response_json = json.dumps(data)
            cached.created_at = datetime.now(timezone.utc)
        else:
            cached = CachedQuery(
                source=source,
                query_hash=query_hash,
                response_json=json.dumps(data),
                ttl_seconds=ttl,
            )
            cache_session.add(cached)

        await cache_session.commit()
        return data
