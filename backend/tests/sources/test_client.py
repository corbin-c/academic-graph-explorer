import pytest

from app.sources.client import HttpSparqlClient

ENDPOINT = "https://example.org/sparql"


class TestHttpSparqlClient:
    @pytest.mark.asyncio
    async def test_query_sends_post_to_endpoint(self, httpx_mock):
        httpx_mock.add_response(
            url=ENDPOINT,
            method="POST",
            json={"results": {"bindings": []}},
        )

        client = HttpSparqlClient(ENDPOINT)
        result = await client.query("SELECT * WHERE { ?s ?p ?o } LIMIT 1")

        assert result == {"results": {"bindings": []}}

        # Verify the request was made correctly
        request = httpx_mock.get_request()
        assert request.method == "POST"
        assert request.url == ENDPOINT
        assert "application/sparql-results+json" in request.headers["Accept"]

    @pytest.mark.asyncio
    async def test_query_returns_json_dict(self, httpx_mock):
        httpx_mock.add_response(
            url=ENDPOINT,
            method="POST",
            json={"head": {"vars": ["s", "p", "o"]}, "results": {"bindings": []}},
        )

        client = HttpSparqlClient(ENDPOINT)
        result = await client.query("SELECT * WHERE { ?s ?p ?o }")

        assert isinstance(result, dict)
        assert "head" in result
        assert "results" in result

    @pytest.mark.asyncio
    async def test_query_raises_on_http_error(self, httpx_mock):
        httpx_mock.add_response(
            url=ENDPOINT,
            method="POST",
            status_code=500,
        )

        client = HttpSparqlClient(ENDPOINT)
        with pytest.raises(Exception):
            await client.query("BROKEN QUERY")
