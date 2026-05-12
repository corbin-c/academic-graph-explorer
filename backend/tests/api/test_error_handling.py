"""Tests for SPARQL error handling (502 responses)."""

import pytest


class TestSparqlErrorHandling:
    @pytest.mark.asyncio
    async def test_person_502_on_sparql_error(self, async_client, httpx_mock):
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            status_code=500,
        )

        response = await async_client.get("/api/person/121375307")
        assert response.status_code == 502

    @pytest.mark.asyncio
    async def test_organization_502_on_sparql_error(self, async_client, httpx_mock):
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            status_code=500,
        )

        response = await async_client.get("/api/organization/227816196")
        assert response.status_code == 502

    @pytest.mark.asyncio
    async def test_publication_502_on_sparql_error(self, async_client, httpx_mock):
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            status_code=500,
        )

        response = await async_client.get("/api/publication/123456789")
        assert response.status_code == 502
