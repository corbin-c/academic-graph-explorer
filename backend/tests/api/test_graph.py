"""Tests for the Graph traversal API endpoint."""

import pytest


class TestGraphValidation:
    @pytest.mark.asyncio
    async def test_missing_root_returns_422(self, async_client):
        response = await async_client.get("/api/graph/")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_type_returns_422(self, async_client):
        response = await async_client.get(
            "/api/graph/", params={"root": "http://www.idref.fr/001/id"}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_type_returns_422(self, async_client):
        response = await async_client.get(
            "/api/graph/",
            params={"root": "http://www.idref.fr/001/id", "type": "banana"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_depth_zero_returns_422(self, async_client):
        response = await async_client.get(
            "/api/graph/",
            params={
                "root": "http://www.idref.fr/001/id",
                "type": "person",
                "depth": 0,
            },
        )
        assert response.status_code == 422


class TestGraphDepthOne:
    @pytest.mark.asyncio
    async def test_single_node_no_edges(self, async_client, httpx_mock):
        """Depth-1 traversal: just the root entity, no additional queries."""
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={
                "results": {
                    "bindings": [
                        {"name": {"type": "literal", "value": "Alice"}},
                    ]
                }
            },
        )
        # Contributions query (runs at depth 0 < 1, returns empty)
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={"results": {"bindings": []}},
        )

        response = await async_client.get(
            "/api/graph/",
            params={
                "root": "http://www.idref.fr/001/id",
                "type": "person",
                "depth": 1,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) == 1
        assert data["nodes"][0]["label"] == "Alice"
        assert data["nodes"][0]["type"] == "person"

    @pytest.mark.asyncio
    async def test_person_with_org_inline(self, async_client, httpx_mock):
        """Person entity query returns org inline — edge created at depth 1."""
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={
                "results": {
                    "bindings": [
                        {
                            "name": {"type": "literal", "value": "Alice"},
                            "org": {
                                "type": "uri",
                                "value": "http://www.idref.fr/org1/id",
                            },
                            "orgName": {"type": "literal", "value": "CNRS"},
                        },
                    ]
                }
            },
        )
        # Contributions query
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={"results": {"bindings": []}},
        )
        # Org entity query for the inline org
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={
                "results": {
                    "bindings": [
                        {"name": {"type": "literal", "value": "CNRS"}},
                    ]
                }
            },
        )

        response = await async_client.get(
            "/api/graph/",
            params={
                "root": "http://www.idref.fr/001/id",
                "type": "person",
                "depth": 1,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1
        assert data["edges"][0]["type"] == "affiliatedWith"


class TestGraphDepthTwo:
    @pytest.mark.asyncio
    async def test_person_to_pubs_via_contributions(self, async_client, httpx_mock):
        """Depth-2: person -> contributions -> publication entities."""
        # 1. Person entity query
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={
                "results": {
                    "bindings": [
                        {"name": {"type": "literal", "value": "Alice"}},
                        {
                            "org": {
                                "type": "uri",
                                "value": "http://www.idref.fr/org1/id",
                            },
                            "orgName": {"type": "literal", "value": "CNRS"},
                        },
                    ]
                }
            },
        )
        # 2. Person contributions query
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={
                "results": {
                    "bindings": [
                        {
                            "doc": {
                                "type": "uri",
                                "value": "http://www.idref.fr/pub1/id",
                            },
                            "title": {"type": "literal", "value": "My Paper"},
                            "role": {"type": "literal", "value": "author"},
                            "author_name": {"type": "literal", "value": "Bob"},
                        },
                    ]
                }
            },
        )
        # 3. Org entity query
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={
                "results": {
                    "bindings": [
                        {"name": {"type": "literal", "value": "CNRS"}},
                    ]
                }
            },
        )
        # 4. Org members query
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={"results": {"bindings": []}},
        )
        # 5. Org publications query (doc extraction; author extraction reuses cache)
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={"results": {"bindings": []}},
        )
        # NOTE: 2nd org publications call (author extraction) uses cached result
        # — no HTTP call, no mock consumed. Next mock (#6) goes to pub entity.
        # 6. Publication entity query
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={
                "results": {
                    "bindings": [
                        {"title": {"type": "literal", "value": "My Paper"}},
                    ]
                }
            },
        )
        # 7. Publication persons query
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={"results": {"bindings": []}},
        )
        # 8. Publication organizations query
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={"results": {"bindings": []}},
        )

        response = await async_client.get(
            "/api/graph/",
            params={
                "root": "http://www.idref.fr/001/id",
                "type": "person",
                "depth": 2,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) == 3
        edge_types = {e["type"] for e in data["edges"]}
        assert "authorOf" in edge_types or "author" in edge_types or "relatedTo" in edge_types
        assert "affiliatedWith" in edge_types

    @pytest.mark.asyncio
    async def test_deduplication(self, async_client, httpx_mock):
        """Same entity discovered via two paths should appear once."""
        # 1. Person entity query + inline org
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={
                "results": {
                    "bindings": [
                        {"name": {"type": "literal", "value": "Alice"}},
                        {
                            "org": {
                                "type": "uri",
                                "value": "http://www.idref.fr/org1/id",
                            },
                            "orgName": {"type": "literal", "value": "CNRS"},
                        },
                    ]
                }
            },
        )
        # 2. Contributions query
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={
                "results": {
                    "bindings": [
                        {
                            "doc": {
                                "type": "uri",
                                "value": "http://www.idref.fr/pub1/id",
                            },
                            "title": {"type": "literal", "value": "Paper"},
                        },
                    ]
                }
            },
        )
        # 3. Org entity query
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={
                "results": {
                    "bindings": [
                        {"name": {"type": "literal", "value": "CNRS"}},
                    ]
                }
            },
        )
        # 4. Org members query
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={"results": {"bindings": []}},
        )
        # 5. Org publications query (doc extraction; author extraction reuses cache)
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={"results": {"bindings": []}},
        )
        # 6. Publication entity query
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={
                "results": {
                    "bindings": [
                        {"title": {"type": "literal", "value": "Paper"}},
                    ]
                }
            },
        )
        # 7. Publication persons query
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={"results": {"bindings": []}},
        )
        # 8. Publication organizations query
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={"results": {"bindings": []}},
        )

        response = await async_client.get(
            "/api/graph/",
            params={
                "root": "http://www.idref.fr/001/id",
                "type": "person",
                "depth": 2,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) == 3

    @pytest.mark.asyncio
    async def test_root_not_found_returns_404(self, async_client, httpx_mock):
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={"results": {"bindings": []}},
        )

        response = await async_client.get(
            "/api/graph/",
            params={
                "root": "http://www.idref.fr/bad/id",
                "type": "person",
                "depth": 1,
            },
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_sparql_error_graceful_recovery(self, async_client, httpx_mock):
        """Individual SPARQL failure should not crash traversal."""
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json={
                "results": {
                    "bindings": [
                        {"name": {"type": "literal", "value": "Alice"}},
                    ]
                }
            },
        )
        # Contributions query fails
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            status_code=500,
        )

        response = await async_client.get(
            "/api/graph/",
            params={
                "root": "http://www.idref.fr/001/id",
                "type": "person",
                "depth": 2,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) == 1
