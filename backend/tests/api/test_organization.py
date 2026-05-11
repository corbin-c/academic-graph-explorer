import pytest


class TestGetOrganization:
    @pytest.mark.asyncio
    async def test_get_organization_by_ppn(self, async_client, httpx_mock):
        """GET /api/organization/{ppn} returns org details."""
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={
                "results": {
                    "bindings": [
                        {
                            "name": {
                                "value": "École des hautes études en sciences sociales"
                            },
                            "note": {"value": "Paris, France. Fondée en 1975."},
                        }
                    ]
                }
            },
        )

        response = await async_client.get("/api/organization/227816196")
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == "227816196"
        assert data["name"] == "École des hautes études en sciences sociales"
        assert data["note"] == "Paris, France. Fondée en 1975."

    @pytest.mark.asyncio
    async def test_get_organization_by_full_uri(self, async_client, httpx_mock):
        """GET /api/organization with full URI works."""
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={"results": {"bindings": [{"name": {"value": "CNRS"}}]}},
        )

        response = await async_client.get(
            "/api/organization/http%3A%2F%2Fwww.idref.fr%2F227816196%2Fid"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "CNRS"
        assert data["note"] is None

    @pytest.mark.asyncio
    async def test_get_organization_not_found(self, async_client, httpx_mock):
        """GET /api/organization/{unknown_ppn} returns 404."""
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={"results": {"bindings": []}},
        )

        response = await async_client.get("/api/organization/99999999")
        assert response.status_code == 404
