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
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={"results": {"bindings": []}},
        )

        response = await async_client.get("/api/organization/99999999")
        assert response.status_code == 404


class TestOrganizationMembers:
    @pytest.mark.asyncio
    async def test_get_members(self, async_client, httpx_mock):
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={
                "results": {
                    "bindings": [
                        {
                            "person": {"value": "http://www.idref.fr/139753753/id"},
                            "name": {"value": "Dacos, Marin (1971-....)"},
                        },
                        {
                            "person": {"value": "http://www.idref.fr/03322286X/id"},
                            "name": {"value": "Dacos, Nicole"},
                        },
                    ]
                }
            },
        )

        response = await async_client.get("/api/organization/227816196/members")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == "http://www.idref.fr/139753753/id"
        assert data[0]["name"] == "Dacos, Marin (1971-....)"
        assert data[1]["name"] == "Dacos, Nicole"

    @pytest.mark.asyncio
    async def test_get_members_empty(self, async_client, httpx_mock):
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={"results": {"bindings": []}},
        )

        response = await async_client.get("/api/organization/999/members")
        assert response.status_code == 200
        assert response.json() == []


class TestOrganizationPublications:
    @pytest.mark.asyncio
    async def test_get_publications(self, async_client, httpx_mock):
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={
                "results": {
                    "bindings": [
                        {
                            "doc": {"value": "http://www.idref.fr/001/id"},
                            "title": {"value": "A Groundbreaking Study"},
                            "author_name": {"value": "Smith, John"},
                        },
                        {
                            "doc": {"value": "http://www.idref.fr/002/id"},
                            "title": {"value": "Another Paper"},
                        },
                    ]
                }
            },
        )

        response = await async_client.get("/api/organization/227816196/publications")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["title"] == "A Groundbreaking Study"
        assert data[0]["author_name"] == "Smith, John"
        assert data[1]["author_name"] is None

    @pytest.mark.asyncio
    async def test_get_publications_empty(self, async_client, httpx_mock):
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={"results": {"bindings": []}},
        )

        response = await async_client.get("/api/organization/999/publications")
        assert response.status_code == 200
        assert response.json() == []
