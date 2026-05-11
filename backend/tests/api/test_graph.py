import pytest

IDREF = "https://data.idref.fr/sparql"


class TestGraphTraversalValidation:
    """Input validation tests (no SPARQL mocking needed)."""

    @pytest.mark.asyncio
    async def test_missing_root_returns_422(self, async_client):
        response = await async_client.get("/api/graph/", params={"type": "person"})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_type_returns_422(self, async_client):
        response = await async_client.get("/api/graph/", params={"root": "121375307"})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_type_returns_422(self, async_client):
        response = await async_client.get(
            "/api/graph/", params={"root": "121375307", "type": "invalid"}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_depth_zero_returns_422(self, async_client):
        response = await async_client.get(
            "/api/graph/", params={"root": "121375307", "type": "person", "depth": 0}
        )
        assert response.status_code == 422


class TestDepthOne:
    """Depth 1 — only the root entity, no edges."""

    @pytest.mark.asyncio
    async def test_person_depth_one(self, async_client, httpx_mock):
        # Response 1: person.sparql (entity info, no orgs inline)
        httpx_mock.add_response(
            url=IDREF,
            method="POST",
            json={
                "results": {
                    "bindings": [
                        {"name": {"value": "Dacos, Marin"}},
                    ]
                }
            },
        )
        # Response 2: person_contributions.sparql (no publications)
        httpx_mock.add_response(
            url=IDREF,
            method="POST",
            json={"results": {"bindings": []}},
        )

        response = await async_client.get(
            "/api/graph/",
            params={
                "root": "http://www.idref.fr/121375307/id",
                "type": "person",
                "depth": 1,
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert data["center"]["id"] == "http://www.idref.fr/121375307/id"
        assert data["center"]["label"] == "Dacos, Marin"
        assert data["center"]["type"] == "person"
        assert len(data["nodes"]) == 1
        assert len(data["edges"]) == 0


class TestDepthTwoPersonOrgs:
    """Depth 2 — person with affiliated organizations."""

    @pytest.mark.asyncio
    async def test_person_with_one_org(self, async_client, httpx_mock):
        # Response 1: person.sparql (entity info + orgs inline)
        httpx_mock.add_response(
            url=IDREF,
            method="POST",
            json={
                "results": {
                    "bindings": [
                        {
                            "name": {"value": "Dacos, Marin"},
                            "org": {"value": "http://www.idref.fr/227816196/id"},
                            "orgName": {"value": "EHESS"},
                        }
                    ]
                }
            },
        )
        # Response 2: person_contributions.sparql (no co-authored pubs)
        httpx_mock.add_response(
            url=IDREF,
            method="POST",
            json={"results": {"bindings": []}},
        )
        # Response 3: organization.sparql (entity info for EHESS)
        httpx_mock.add_response(
            url=IDREF,
            method="POST",
            json={
                "results": {
                    "bindings": [
                        {
                            "name": {
                                "value": "École des hautes études en sciences sociales"
                            }
                        },
                    ]
                }
            },
        )
        # Response 4: organization_members.sparql (no members)
        httpx_mock.add_response(
            url=IDREF,
            method="POST",
            json={"results": {"bindings": []}},
        )
        # Response 5: organization_publications.sparql (no pubs)
        httpx_mock.add_response(
            url=IDREF,
            method="POST",
            json={"results": {"bindings": []}},
        )

        response = await async_client.get(
            "/api/graph/",
            params={"root": "121375307", "type": "person", "depth": 2},
        )

        assert response.status_code == 200
        data = response.json()

        # 2 nodes: person + org
        assert len(data["nodes"]) == 2
        # 1 edge: person → org (AFFILIATED_WITH)
        assert len(data["edges"]) == 1
        assert data["edges"][0]["type"] == "affiliatedWith"
        assert data["edges"][0]["source"] == "http://www.idref.fr/121375307/id"
        assert data["edges"][0]["target"] == "http://www.idref.fr/227816196/id"


class TestDeduplication:
    """Dedup — same entity or edge should only appear once."""

    @pytest.mark.asyncio
    async def test_same_org_via_multiple_paths(self, async_client, httpx_mock):
        # person.sparql → returns 2 orgs (CNRS, EHESS)
        httpx_mock.add_response(
            url=IDREF,
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
        # person_contributions.sparql
        httpx_mock.add_response(
            url=IDREF,
            method="POST",
            json={"results": {"bindings": []}},
        )
        # organization.sparql for CNRS
        httpx_mock.add_response(
            url=IDREF,
            method="POST",
            json={
                "results": {
                    "bindings": [{"name": {"value": "CNRS"}}],
                }
            },
        )
        # org_members for CNRS → returns the same person we started from
        httpx_mock.add_response(
            url=IDREF,
            method="POST",
            json={
                "results": {
                    "bindings": [
                        {
                            "person": {"value": "http://www.idref.fr/121375307/id"},
                            "name": {"value": "Dacos, Marin"},
                        }
                    ]
                }
            },
        )
        # org_publications for CNRS
        httpx_mock.add_response(
            url=IDREF,
            method="POST",
            json={"results": {"bindings": []}},
        )
        # organization.sparql for EHESS
        httpx_mock.add_response(
            url=IDREF,
            method="POST",
            json={
                "results": {
                    "bindings": [{"name": {"value": "EHESS"}}],
                }
            },
        )
        # org_members for EHESS → also returns the same person
        httpx_mock.add_response(
            url=IDREF,
            method="POST",
            json={
                "results": {
                    "bindings": [
                        {
                            "person": {"value": "http://www.idref.fr/121375307/id"},
                            "name": {"value": "Dacos, Marin"},
                        }
                    ]
                }
            },
        )
        # org_publications for EHESS
        httpx_mock.add_response(
            url=IDREF,
            method="POST",
            json={"results": {"bindings": []}},
        )

        response = await async_client.get(
            "/api/graph/",
            params={"root": "121375307", "type": "person", "depth": 2},
        )

        assert response.status_code == 200
        data = response.json()

        # 3 nodes: person + CNRS + EHESS (no duplicates)
        assert len(data["nodes"]) == 3
        # 2 edges: person→CNRS, person→EHESS (no reverse edges from org_members)
        assert len(data["edges"]) == 2


class TestErrorHandling:
    """Graceful handling of SPARQL failures during traversal."""

    @pytest.mark.asyncio
    async def test_root_not_found(self, async_client, httpx_mock):
        httpx_mock.add_response(
            url=IDREF,
            method="POST",
            json={"results": {"bindings": []}},
        )

        response = await async_client.get(
            "/api/graph/",
            params={"root": "99999999", "type": "person", "depth": 1},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_sparql_error_on_relationships(self, async_client, httpx_mock):
        """When a relationship query fails, traversal continues."""
        # person.sparql → returns name + 1 org
        httpx_mock.add_response(
            url=IDREF,
            method="POST",
            json={
                "results": {
                    "bindings": [
                        {
                            "name": {"value": "Dacos, Marin"},
                            "org": {"value": "http://www.idref.fr/001/id"},
                            "orgName": {"value": "CNRS"},
                        }
                    ]
                }
            },
        )
        # person_contributions.sparql → fails (500)
        httpx_mock.add_response(
            url=IDREF,
            method="POST",
            status_code=500,
        )
        # organization.sparql for CNRS
        httpx_mock.add_response(
            url=IDREF,
            method="POST",
            json={
                "results": {
                    "bindings": [{"name": {"value": "CNRS"}}],
                }
            },
        )
        # org_members for CNRS
        httpx_mock.add_response(
            url=IDREF,
            method="POST",
            json={"results": {"bindings": []}},
        )
        # org_publications for CNRS
        httpx_mock.add_response(
            url=IDREF,
            method="POST",
            json={"results": {"bindings": []}},
        )

        response = await async_client.get(
            "/api/graph/",
            params={"root": "121375307", "type": "person", "depth": 2},
        )

        # Should still succeed — just without the publications edge
        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) == 2  # person + CNRS
        assert len(data["edges"]) == 1  # just the AFFILIATED_WITH edge
