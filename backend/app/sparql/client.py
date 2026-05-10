"""
SPARQL client for querying external RDF data sources.
"""

from abc import ABC, abstractmethod

import httpx

# Many endpoints return plain JSON rather than the stricter SPARQL results format.
# We accept both.
SPARQL_ACCEPT_HEADERS = "application/sparql-results+json, application/json;q=0.9"


class SparqlClient(ABC):
    """Abstract client for a SPARQL endpoint."""

    @abstractmethod
    async def query(self, sparql: str) -> dict:
        """Execute a SPARQL query and return results as JSON."""
        ...


class HttpSparqlClient(SparqlClient):
    """SPARQL client that communicates over HTTP."""

    def __init__(self, endpoint_url: str):
        self.endpoint_url = endpoint_url

    async def query(self, sparql: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.endpoint_url,
                data={"query": sparql},
                headers={"Accept": SPARQL_ACCEPT_HEADERS},
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()
