import pytest

from app.sources.hal.sparql import HAL_ENDPOINT, HalSparqlClient


class TestHalSparqlClient:
    @pytest.mark.asyncio
    async def test_queries_hal_endpoint(self, httpx_mock):
        httpx_mock.add_response(
            url=HAL_ENDPOINT,
            method="POST",
            json={"results": {"bindings": []}},
        )

        client = HalSparqlClient()
        result = await client.query("SELECT * WHERE { ?s ?p ?o } LIMIT 1")

        assert result == {"results": {"bindings": []}}
        request = httpx_mock.get_request()
        assert request.url == HAL_ENDPOINT

    @pytest.mark.asyncio
    async def test_accept_header_includes_sparql_results_format(self, httpx_mock):
        httpx_mock.add_response(
            url=HAL_ENDPOINT,
            method="POST",
            json={},
        )

        client = HalSparqlClient()
        await client.query("ASK { ?s ?p ?o }")

        request = httpx_mock.get_request()
        assert "application/sparql-results+json" in request.headers["Accept"]
        assert "application/json" in request.headers["Accept"]
