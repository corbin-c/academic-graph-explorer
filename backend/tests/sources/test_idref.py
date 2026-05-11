import pytest

from app.sources.idref.sparql import IDREF_ENDPOINT, IdRefSparqlClient


class TestIdRefSparqlClient:
    @pytest.mark.asyncio
    async def test_queries_idref_endpoint(self, httpx_mock):
        httpx_mock.add_response(
            url=IDREF_ENDPOINT,
            method="POST",
            json={"results": {"bindings": []}},
        )

        client = IdRefSparqlClient()
        result = await client.query("SELECT * WHERE { ?s ?p ?o } LIMIT 1")

        assert result == {"results": {"bindings": []}}
        request = httpx_mock.get_request()
        assert request.url == IDREF_ENDPOINT
