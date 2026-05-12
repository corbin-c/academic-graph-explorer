"""Tests for the Organization API endpoint."""

import pytest


class TestGetOrganization:
    @pytest.mark.asyncio
    async def test_get_organization_by_ppn(self, async_client, httpx_mock):
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={
                "results": {
                    "bindings": [
                        {
                            "name": {"type": "literal", "value": "CNRS"},
                            "note": {"type": "literal", "value": "Research org"},
                        },
                    ]
                }
            },
        )

        response = await async_client.get("/api/organization/227816196")
        assert response.status_code == 200
        data = response.json()
        assert data["label"] == "CNRS"
        assert data["type"] == "organization"
        assert data["note"] == "Research org"

    @pytest.mark.asyncio
    async def test_get_organization_by_full_uri(self, async_client, httpx_mock):
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={
                "results": {
                    "bindings": [
                        {"name": {"type": "literal", "value": "Some Org"}},
                    ]
                }
            },
        )

        response = await async_client.get(
            "/api/organization/http%3A%2F%2Fwww.idref.fr%2F999%2Fid"
        )
        assert response.status_code == 200
        assert response.json()["label"] == "Some Org"

    @pytest.mark.asyncio
    async def test_get_organization_not_found(self, async_client, httpx_mock):
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={"results": {"bindings": []}},
        )

        response = await async_client.get("/api/organization/999999999")
        assert response.status_code == 404
