import re

import pytest


class TestSearch:
    @pytest.mark.asyncio
    async def test_search_returns_simplified_results(self, async_client, httpx_mock):
        """A successful search returns SearchResult objects with name, ppn, identifiers."""
        httpx_mock.add_response(
            url=re.compile(r"https://www\.idref\.fr/Sru/Solr\?.*"),
            method="GET",
            json={
                "response": {
                    "docs": [
                        {
                            "affcourt_z": "Dacos, Marin (1971-....)",
                            "ppn_z": "139753753",
                            "idsext_s": [
                                "0000000385709539",
                                "0000-0002-9361-5295",
                            ],
                        },
                        {
                            "affcourt_z": "Dacos, Antonin",
                            "ppn_z": "27232261X",
                        },
                    ]
                }
            },
        )

        response = await async_client.get("/api/search/", params={"q": "Dacos"})
        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2

        assert data[0]["name"] == "Dacos, Marin (1971-....)"
        assert data[0]["ppn"] == "139753753"
        assert data[0]["identifiers"] == ["0000000385709539", "0000-0002-9361-5295"]

        assert data[1]["name"] == "Dacos, Antonin"
        assert data[1]["ppn"] == "27232261X"
        assert data[1]["identifiers"] == []

    @pytest.mark.asyncio
    async def test_search_empty_results(self, async_client, httpx_mock):
        """When IdRef returns no docs, the API returns an empty list."""
        httpx_mock.add_response(
            url=re.compile(r"https://www\.idref\.fr/Sru/Solr\?.*"),
            method="GET",
            json={"response": {"docs": []}},
        )

        response = await async_client.get("/api/search/", params={"q": "no_match"})
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_search_missing_query_returns_422(self, async_client):
        response = await async_client.get("/api/search/")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_search_empty_query_returns_422(self, async_client):
        response = await async_client.get("/api/search/", params={"q": ""})
        assert response.status_code == 422
