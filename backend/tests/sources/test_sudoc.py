import pytest

from app.sources.sudoc.sparql import SudocClient

SUDOC_RDF_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:dc="http://purl.org/dc/elements/1.1/"
         xmlns:dcterms="http://purl.org/dc/terms/"
         xmlns:marcrel="http://id.loc.gov/vocabulary/relators/">
  <rdf:Description rdf:about="https://www.sudoc.fr/123456789">
    <dc:title>Example Publication Title</dc:title>
    <dc:date>2023</dc:date>
    <dcterms:abstract>An abstract of the publication.</dcterms:abstract>
  </rdf:Description>
</rdf:RDF>"""


class TestSudocClient:
    @pytest.mark.asyncio
    async def test_fetch_rdf_returns_text(self, httpx_mock):
        httpx_mock.add_response(
            url="https://www.sudoc.fr/123456789.rdf",
            method="GET",
            text=SUDOC_RDF_XML,
        )

        client = SudocClient()
        result = await client.fetch_rdf("123456789")

        assert "Example Publication Title" in result
        assert "123456789" in result

    @pytest.mark.asyncio
    async def test_fetch_rdf_sends_get_request(self, httpx_mock):
        httpx_mock.add_response(
            url="https://www.sudoc.fr/999.rdf",
            method="GET",
            text="<rdf:RDF></rdf:RDF>",
        )

        client = SudocClient()
        await client.fetch_rdf("999")

        request = httpx_mock.get_request()
        assert request.method == "GET"
        assert request.url == "https://www.sudoc.fr/999.rdf"

    @pytest.mark.asyncio
    async def test_fetch_rdf_raises_on_error(self, httpx_mock):
        httpx_mock.add_response(
            url="https://www.sudoc.fr/bad.rdf",
            method="GET",
            status_code=404,
        )

        client = SudocClient()
        with pytest.raises(Exception):
            await client.fetch_rdf("bad")
