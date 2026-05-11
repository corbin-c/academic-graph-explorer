"""Test SPARQL error handling in API endpoints."""

import pytest


class TestSparqlErrorHandling:
    @pytest.mark.asyncio
    async def test_person_endpoint_returns_502_on_sparql_error(
        self, async_client, httpx_mock
    ):
        """When IdRef SPARQL returns 500, the API should return 502."""
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            status_code=500,
        )

        response = await async_client.get("/api/person/121375307")
        assert response.status_code == 502

    @pytest.mark.asyncio
    async def test_organization_endpoint_returns_502_on_sparql_error(
        self, async_client, httpx_mock
    ):
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            status_code=500,
        )

        response = await async_client.get("/api/organization/227816196")
        assert response.status_code == 502

    @pytest.mark.asyncio
    async def test_publication_endpoint_returns_502_on_sparql_error(
        self, async_client, httpx_mock
    ):
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            status_code=500,
        )

        response = await async_client.get("/api/publication/242351441")
        assert response.status_code == 502
