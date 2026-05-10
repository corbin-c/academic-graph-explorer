import pytest

from app.sources.persee.sparql import PERSEE_ENDPOINT, PerseeSparqlClient


class TestPerseeSparqlClient:
    @pytest.mark.asyncio
    async def test_queries_persee_endpoint(self, httpx_mock):
        httpx_mock.add_response(
            url=PERSEE_ENDPOINT,
            method="POST",
            json={"results": {"bindings": []}},
        )

        client = PerseeSparqlClient()
        result = await client.query("SELECT * WHERE { ?s ?p ?o } LIMIT 1")

        assert result == {"results": {"bindings": []}}
        request = httpx_mock.get_request()
        assert request.url == PERSEE_ENDPOINT

    @pytest.mark.asyncio
    async def test_accept_header_includes_sparql_results_format(self, httpx_mock):
        httpx_mock.add_response(
            url=PERSEE_ENDPOINT,
            method="POST",
            json={},
        )

        client = PerseeSparqlClient()
        await client.query("ASK { ?s ?p ?o }")

        request = httpx_mock.get_request()
        assert "application/sparql-results+json" in request.headers["Accept"]
        assert "application/json" in request.headers["Accept"]
