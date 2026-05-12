"""Tests for the Person API endpoint."""

import pytest


class TestGetPerson:
    @pytest.mark.asyncio
    async def test_get_person_by_ppn(self, async_client, httpx_mock):
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={
                "results": {
                    "bindings": [
                        {
                            "name": {"type": "literal", "value": "Marin Dacos"},
                        },
                    ]
                }
            },
        )

        response = await async_client.get("/api/person/121375307")
        assert response.status_code == 200
        data = response.json()
        assert data["label"] == "Marin Dacos"
        assert data["type"] == "person"
        assert data["organizations"] == []

    @pytest.mark.asyncio
    async def test_get_person_with_organizations(self, async_client, httpx_mock):
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={
                "results": {
                    "bindings": [
                        {
                            "name": {"type": "literal", "value": "Marin Dacos"},
                            "org": {
                                "type": "uri",
                                "value": "http://www.idref.fr/227816196/id",
                            },
                            "orgName": {"type": "literal", "value": "CNRS"},
                        },
                        {
                            "name": {"type": "literal", "value": "Marin Dacos"},
                            "org": {
                                "type": "uri",
                                "value": "http://www.idref.fr/001/id",
                            },
                            "orgName": {"type": "literal", "value": "EHESS"},
                        },
                    ]
                }
            },
        )

        response = await async_client.get("/api/person/121375307")
        assert response.status_code == 200
        data = response.json()
        assert len(data["organizations"]) == 2
        assert data["organizations"][0]["label"] == "CNRS"
        assert data["organizations"][1]["label"] == "EHESS"

    @pytest.mark.asyncio
    async def test_get_person_by_full_uri(self, async_client, httpx_mock):
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={
                "results": {
                    "bindings": [
                        {"name": {"type": "literal", "value": "Someone"}},
                    ]
                }
            },
        )

        response = await async_client.get("/api/person/999")
        assert response.status_code == 200
        assert response.json()["label"] == "Someone"

    @pytest.mark.asyncio
    async def test_get_person_not_found(self, async_client, httpx_mock):
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={"results": {"bindings": []}},
        )

        response = await async_client.get("/api/person/999999999")
        assert response.status_code == 404
