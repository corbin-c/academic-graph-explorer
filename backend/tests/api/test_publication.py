"""Tests for the Publication API endpoint."""

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
        assert data["label"] == "Test Publication"
        assert data["type"] == "publication"
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
    async def test_get_publication_deduplicates_identifiers(
        self, async_client, httpx_mock
    ):
        """Duplicate sameAs identifiers should be collapsed."""
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
                            "title": {"type": "literal", "value": "Paper with DOI"},
                            "doi": {"type": "literal", "value": "10.1234/example"},
                        },
                    ]
                }
            },
        )

        response = await async_client.get("/api/publication/123456789")
        assert response.status_code == 200
        data = response.json()
        assert data["doi"] == "10.1234/example"
