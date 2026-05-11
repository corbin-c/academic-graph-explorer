"""Tests for the Publication API endpoints."""

import pytest


class TestGetPublication:
    @pytest.mark.asyncio
    async def test_get_publication_by_ppn(self, async_client, httpx_mock):
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={
                "results": {
                    "bindings": [
                        {
                            "title": {"type": "literal", "value": "Test Publication"},
                        },
                    ]
                }
            },
        )

        response = await async_client.get("/api/publication/123456789")
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Publication"
        assert data["doi"] is None
        assert data["identifiers"] == []

    @pytest.mark.asyncio
    async def test_get_publication_with_identifiers(self, async_client, httpx_mock):
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={
                "results": {
                    "bindings": [
                        {"title": {"type": "literal", "value": "Paper"}},
                        {
                            "sameAs": {
                                "type": "uri",
                                "value": "https://hal.science/hal-001",
                            }
                        },
                    ]
                }
            },
        )

        response = await async_client.get("/api/publication/123456789")
        assert response.status_code == 200
        data = response.json()
        assert len(data["identifiers"]) == 1
        assert data["identifiers"][0]["scheme"] == "owl:sameAs"

    @pytest.mark.asyncio
    async def test_get_publication_not_found(self, async_client, httpx_mock):
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={"results": {"bindings": []}},
        )

        response = await async_client.get("/api/publication/999999999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_publication_with_doi(self, async_client, httpx_mock):
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={
                "results": {
                    "bindings": [
                        {
                            "title": {
                                "type": "literal",
                                "value": "Paper with DOI",
                            },
                            "doi": {
                                "type": "literal",
                                "value": "10.1234/example",
                            },
                        },
                    ]
                }
            },
        )

        response = await async_client.get("/api/publication/123456789")
        assert response.status_code == 200
        data = response.json()
        assert data["doi"] == "10.1234/example"


class TestPublicationPersons:
    @pytest.mark.asyncio
    async def test_get_publication_persons(self, async_client, httpx_mock):
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={
                "results": {
                    "bindings": [
                        {
                            "person": {
                                "type": "uri",
                                "value": "http://www.idref.fr/001/id",
                            },
                            "person_name": {
                                "type": "literal",
                                "value": "Alice",
                            },
                            "person_role": {
                                "type": "literal",
                                "value": "author",
                            },
                        },
                        {
                            "person": {
                                "type": "uri",
                                "value": "http://www.idref.fr/002/id",
                            },
                            "person_name": {
                                "type": "literal",
                                "value": "Bob",
                            },
                        },
                    ]
                }
            },
        )

        response = await async_client.get("/api/publication/123/persons")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "Alice"
        assert data[0]["role"] == "author"
        assert data[1]["name"] == "Bob"
        assert data[1]["role"] is None

    @pytest.mark.asyncio
    async def test_get_publication_persons_empty(self, async_client, httpx_mock):
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={"results": {"bindings": []}},
        )

        response = await async_client.get("/api/publication/123/persons")
        assert response.status_code == 200
        assert response.json() == []


class TestPublicationOrganizations:
    @pytest.mark.asyncio
    async def test_get_publication_organizations(self, async_client, httpx_mock):
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={
                "results": {
                    "bindings": [
                        {
                            "org": {
                                "type": "uri",
                                "value": "http://www.idref.fr/001/id",
                            },
                            "org_name": {
                                "type": "literal",
                                "value": "CNRS",
                            },
                            "org_role": {
                                "type": "literal",
                                "value": "host",
                            },
                        },
                    ]
                }
            },
        )

        response = await async_client.get("/api/publication/123/organizations")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "CNRS"
        assert data[0]["role"] == "host"

    @pytest.mark.asyncio
    async def test_get_publication_organizations_empty(self, async_client, httpx_mock):
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={"results": {"bindings": []}},
        )

        response = await async_client.get("/api/publication/123/organizations")
        assert response.status_code == 200
        assert response.json() == []
