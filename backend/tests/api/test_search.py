import re

import pytest

SOLR_URL = "https://www.idref.fr/Sru/Solr"


class TestSearchValidation:
    @pytest.mark.asyncio
    async def test_missing_query_returns_422(self, async_client):
        response = await async_client.get("/api/search/")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_query_returns_422(self, async_client):
        response = await async_client.get("/api/search/", params={"q": ""})
        assert response.status_code == 422


class TestSearchResults:
    @pytest.mark.asyncio
    async def test_returns_person_and_organization(self, async_client, httpx_mock):
        httpx_mock.add_response(
            url=re.compile(r"^https://www\.idref\.fr/Sru/Solr\?"),
            method="GET",
            json={
                "response": {
                    "numFound": 2,
                    "start": 0,
                    "docs": [
                        {
                            "id": "10158026",
                            "ppn_z": "277163757",
                            "recordtype_z": "a",
                            "affcourt_z": "Dupont, Jean (1970-....)",
                        },
                        {
                            "id": "10711524",
                            "ppn_z": "296944106",
                            "recordtype_z": "b",
                            "affcourt_z": "CNRS",
                        },
                    ],
                }
            },
        )

        response = await async_client.get("/api/search/", params={"q": "Dupont"})
        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2
        assert data[0] == {
            "id": "277163757",
            "name": "Dupont, Jean (1970-....)",
            "type": "person",
        }
        assert data[1] == {
            "id": "296944106",
            "name": "CNRS",
            "type": "organization",
        }

    @pytest.mark.asyncio
    async def test_filters_unknown_recordtypes(self, async_client, httpx_mock):
        httpx_mock.add_response(
            url=re.compile(r"^https://www\.idref\.fr/Sru/Solr\?"),
            method="GET",
            json={
                "response": {
                    "numFound": 1,
                    "start": 0,
                    "docs": [
                        {
                            "id": "999",
                            "ppn_z": "999999999",
                            "recordtype_z": "c",
                            "affcourt_z": "Some Corp Body",
                        },
                    ],
                }
            },
        )

        response = await async_client.get("/api/search/", params={"q": "corp"})
        assert response.status_code == 200
        # Unknown recordtype_z should be filtered out
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_empty_results(self, async_client, httpx_mock):
        httpx_mock.add_response(
            url=re.compile(r"^https://www\.idref\.fr/Sru/Solr\?"),
            method="GET",
            json={
                "response": {
                    "numFound": 0,
                    "start": 0,
                    "docs": [],
                }
            },
        )

        response = await async_client.get(
            "/api/search/", params={"q": "xyznonexistent"}
        )
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_solr_error_returns_502(self, async_client, httpx_mock):
        httpx_mock.add_response(
            url=re.compile(r"^https://www\.idref\.fr/Sru/Solr\?"),
            method="GET",
            status_code=500,
        )

        response = await async_client.get("/api/search/", params={"q": "test"})
        assert response.status_code == 502

    @pytest.mark.asyncio
    async def test_accent_stripping(self, async_client, httpx_mock):
        """Verify that accented queries are normalized before reaching SOLR."""
        httpx_mock.add_response(
            url=re.compile(r"^https://www\.idref\.fr/Sru/Solr\?"),
            method="GET",
            json={
                "response": {
                    "numFound": 1,
                    "start": 0,
                    "docs": [
                        {
                            "id": "1",
                            "ppn_z": "123",
                            "recordtype_z": "a",
                            "affcourt_z": "Ecolier, Éric",
                        },
                    ],
                }
            },
        )

        response = await async_client.get("/api/search/", params={"q": "Éric"})
        assert response.status_code == 200

        # Check that the SOLR query was sanitized (no accents in the URL)
        request = httpx_mock.get_request()
        assert "eric" in str(request.url)
        assert "%C3%89" not in str(request.url)  # No é in the URL
