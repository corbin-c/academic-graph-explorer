import re

import pytest

from app.sources.idref.resources import IdRefResourcesClient
from app.sources.idref.search import IdRefSearchClient
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


class TestIdRefSearchClient:
    @pytest.mark.asyncio
    async def test_search_person_sends_solr_query(self, httpx_mock):
        httpx_mock.add_response(
            url=re.compile(r"https://www\.idref\.fr/Sru/Solr\?"),
            method="GET",
            json={"response": {"docs": []}},
        )

        client = IdRefSearchClient()
        result = await client.search_person("Marin Dacos")

        assert result == {"response": {"docs": []}}
        request = httpx_mock.get_request()
        assert request.method == "GET"
        assert "Marin" in str(request.url)
        assert "Dacos" in str(request.url)

    @pytest.mark.asyncio
    async def test_search_single_word_name(self, httpx_mock):
        httpx_mock.add_response(
            url=re.compile(r"https://www\.idref\.fr/Sru/Solr\?"),
            method="GET",
            json={"response": {"docs": [{"ppn_z": "123"}]}},
        )

        client = IdRefSearchClient()
        result = await client.search_person("Dupont")

        assert len(result["response"]["docs"]) == 1


class TestIdRefResourcesClient:
    @pytest.mark.asyncio
    async def test_get_references(self, httpx_mock):
        httpx_mock.add_response(
            url="https://www.idref.fr/services/references/121375307.json",
            method="GET",
            json={"sudoc": {"result": []}},
        )

        client = IdRefResourcesClient()
        result = await client.get_references("121375307")

        assert result == {"sudoc": {"result": []}}

    @pytest.mark.asyncio
    async def test_get_biblio(self, httpx_mock):
        httpx_mock.add_response(
            url="https://www.idref.fr/services/biblio/121375307.json",
            method="GET",
            json={"sudoc": {"result": {"role": []}}},
        )

        client = IdRefResourcesClient()
        result = await client.get_biblio("121375307")

        assert "sudoc" in result
