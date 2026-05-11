import re

import pytest


class TestGetPerson:
    @pytest.mark.asyncio
    async def test_get_person_by_ppn(self, async_client, httpx_mock):
        """GET /api/person/{ppn} returns person details from IdRef SPARQL."""
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={
                "results": {
                    "bindings": [
                        {
                            "name": {"value": "Dacos, Marin (1971-....)"},
                            "note": {"value": "Ingénieur de recherche au CNRS."},
                            "org": {"value": "http://www.idref.fr/227816196/id"},
                            "orgName": {
                                "value": "École des hautes études en sciences sociales"
                            },
                        }
                    ]
                }
            },
        )

        response = await async_client.get("/api/person/121375307")
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == "121375307"
        assert data["name"] == "Dacos, Marin (1971-....)"
        assert data["note"] == "Ingénieur de recherche au CNRS."
        assert len(data["organizations"]) == 1
        assert (
            data["organizations"][0]["name"]
            == "École des hautes études en sciences sociales"
        )

    @pytest.mark.asyncio
    async def test_get_person_by_full_uri(self, async_client, httpx_mock):
        """GET /api/person with full IdRef URI also works."""
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={
                "results": {
                    "bindings": [
                        {
                            "name": {"value": "Dacos, Marin"},
                            "note": {"value": "Some note."},
                        }
                    ]
                }
            },
        )

        response = await async_client.get(
            "/api/person/http%3A%2F%2Fwww.idref.fr%2F121375307%2Fid"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Dacos, Marin"
        assert data["organizations"] == []

    @pytest.mark.asyncio
    async def test_get_person_not_found(self, async_client, httpx_mock):
        """GET /api/person/{unknown_ppn} returns 404."""
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={"results": {"bindings": []}},
        )

        response = await async_client.get("/api/person/99999999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_person_multiple_orgs(self, async_client, httpx_mock):
        """Person with multiple org memberships returns all of them."""
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={
                "results": {
                    "bindings": [
                        {
                            "name": {"value": "Dacos, Marin"},
                            "org": {"value": "http://www.idref.fr/001/id"},
                            "orgName": {"value": "CNRS"},
                        },
                        {
                            "name": {"value": "Dacos, Marin"},
                            "org": {"value": "http://www.idref.fr/002/id"},
                            "orgName": {"value": "EHESS"},
                        },
                    ]
                }
            },
        )

        response = await async_client.get("/api/person/121375307")
        assert response.status_code == 200
        data = response.json()
        assert len(data["organizations"]) == 2
        assert data["organizations"][0]["name"] == "CNRS"
        assert data["organizations"][1]["name"] == "EHESS"
