"""Tests for the Graph traversal API endpoint."""

import urllib.parse

import pytest

from app.sources.idref import queries as idref_queries

SPARQL_ENDPOINT = "https://data.idref.fr/sparql"


def _query_body(template: str, param: str, uri: str) -> bytes:
    """Return the exact form-encoded SPARQL body httpx will POST.

    The client submits `data={"query": sparql}`, so the wire body is the
    urlencoded query with the entity URI substituted for the template param.
    """
    sparql = template.replace(param, f"<{uri}>")
    return urllib.parse.urlencode({"query": sparql}).encode()


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
    ALICE = "http://www.idref.fr/001/id"
    ORG1 = "http://www.idref.fr/org1/id"
    PUB1 = "http://www.idref.fr/pub1/id"

    @pytest.mark.asyncio
    async def test_person_to_pubs_via_contributions(self, async_client, httpx_mock):
        """Depth-2: person -> contributions -> publication entities."""
        # Person entity query
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(idref_queries.PERSON, "$person", self.ALICE),
            json={
                "results": {
                    "bindings": [
                        {"name": {"type": "literal", "value": "Alice"}},
                        {
                            "org": {"type": "uri", "value": self.ORG1},
                            "orgName": {"type": "literal", "value": "CNRS"},
                        },
                    ]
                }
            },
        )
        # Person contributions query (doc + role)
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(
                idref_queries.PERSON_CONTRIBUTIONS, "$person", self.ALICE
            ),
            json={
                "results": {
                    "bindings": [
                        {
                            "doc": {"type": "uri", "value": self.PUB1},
                            "role": {"type": "literal", "value": "author"},
                        },
                    ]
                }
            },
        )
        # Org entity query
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(
                idref_queries.ORGANIZATION, "$organization", self.ORG1
            ),
            json={
                "results": {
                    "bindings": [
                        {"name": {"type": "literal", "value": "CNRS"}},
                    ]
                }
            },
        )
        # Org members query
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(
                idref_queries.ORGANIZATION_MEMBERS, "$organization", self.ORG1
            ),
            json={"results": {"bindings": []}},
        )
        # Org publications query (single query serves both "doc" and "author" specs)
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(
                idref_queries.ORGANIZATION_PUBLICATIONS, "$organization", self.ORG1
            ),
            json={"results": {"bindings": []}},
        )
        # Publication entity query
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(
                idref_queries.PUBLICATION, "$publication", self.PUB1
            ),
            json={
                "results": {
                    "bindings": [
                        {"title": {"type": "literal", "value": "My Paper"}},
                    ]
                }
            },
        )
        # Publication persons query
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(
                idref_queries.PUBLICATION_PERSONS, "$publication", self.PUB1
            ),
            json={"results": {"bindings": []}},
        )
        # Publication organizations query
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(
                idref_queries.PUBLICATION_ORGANIZATIONS, "$publication", self.PUB1
            ),
            json={"results": {"bindings": []}},
        )

        response = await async_client.get(
            "/api/graph/",
            params={"root": self.ALICE, "type": "person", "depth": 2},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) == 3
        edge_types = {e["type"] for e in data["edges"]}
        assert "author" in edge_types
        assert "affiliatedWith" in edge_types

    @pytest.mark.asyncio
    async def test_deduplication(self, async_client, httpx_mock):
        """Same entity discovered via two paths should appear once."""
        # Person entity query
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(idref_queries.PERSON, "$person", self.ALICE),
            json={
                "results": {
                    "bindings": [
                        {"name": {"type": "literal", "value": "Alice"}},
                        {
                            "org": {"type": "uri", "value": self.ORG1},
                            "orgName": {"type": "literal", "value": "CNRS"},
                        },
                    ]
                }
            },
        )
        # Contributions query
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(
                idref_queries.PERSON_CONTRIBUTIONS, "$person", self.ALICE
            ),
            json={
                "results": {
                    "bindings": [
                        {"doc": {"type": "uri", "value": self.PUB1}},
                    ]
                }
            },
        )
        # Org entity query
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(
                idref_queries.ORGANIZATION, "$organization", self.ORG1
            ),
            json={
                "results": {
                    "bindings": [
                        {"name": {"type": "literal", "value": "CNRS"}},
                    ]
                }
            },
        )
        # Org members query
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(
                idref_queries.ORGANIZATION_MEMBERS, "$organization", self.ORG1
            ),
            json={"results": {"bindings": []}},
        )
        # Org publications query (single query serves both "doc" and "author" specs)
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(
                idref_queries.ORGANIZATION_PUBLICATIONS, "$organization", self.ORG1
            ),
            json={"results": {"bindings": []}},
        )
        # Publication entity query
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(
                idref_queries.PUBLICATION, "$publication", self.PUB1
            ),
            json={
                "results": {
                    "bindings": [
                        {"title": {"type": "literal", "value": "Paper"}},
                    ]
                }
            },
        )
        # Publication persons query
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(
                idref_queries.PUBLICATION_PERSONS, "$publication", self.PUB1
            ),
            json={"results": {"bindings": []}},
        )
        # Publication organizations query
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(
                idref_queries.PUBLICATION_ORGANIZATIONS, "$publication", self.PUB1
            ),
            json={"results": {"bindings": []}},
        )

        response = await async_client.get(
            "/api/graph/",
            params={"root": self.ALICE, "type": "person", "depth": 2},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) == 3

    @pytest.mark.asyncio
    async def test_depth_boundary_second_person_org_not_expanded(
        self, async_client, httpx_mock
    ):
        """A person reached at max depth is a leaf — its inline org is not expanded."""
        bob = "http://www.idref.fr/bob/id"
        org2 = "http://www.idref.fr/org2/id"

        # Root person (Alice) entity query with inline org.
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(idref_queries.PERSON, "$person", self.ALICE),
            json={
                "results": {
                    "bindings": [
                        {
                            "name": {"type": "literal", "value": "Alice"},
                            "org": {"type": "uri", "value": self.ORG1},
                            "orgName": {"type": "literal", "value": "CNRS"},
                        },
                    ]
                }
            },
        )
        # Bob's person entity query — reached at depth 2, has its own inline org.
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(idref_queries.PERSON, "$person", bob),
            json={
                "results": {
                    "bindings": [
                        {
                            "name": {"type": "literal", "value": "Bob"},
                            "org": {"type": "uri", "value": org2},
                            "orgName": {"type": "literal", "value": "BobOrg"},
                        },
                    ]
                }
            },
        )
        # Contributions query (root person) — empty.
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(
                idref_queries.PERSON_CONTRIBUTIONS, "$person", self.ALICE
            ),
            json={"results": {"bindings": []}},
        )
        # Org1 entity query.
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(
                idref_queries.ORGANIZATION, "$organization", self.ORG1
            ),
            json={
                "results": {
                    "bindings": [
                        {"name": {"type": "literal", "value": "CNRS"}},
                    ]
                }
            },
        )
        # Org1 members query — returns Bob.
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(
                idref_queries.ORGANIZATION_MEMBERS, "$organization", self.ORG1
            ),
            json={
                "results": {
                    "bindings": [
                        {
                            "person": {"type": "uri", "value": bob},
                            "name": {"type": "literal", "value": "Bob"},
                        },
                    ]
                }
            },
        )
        # Org1 publications query — empty.
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(
                idref_queries.ORGANIZATION_PUBLICATIONS, "$organization", self.ORG1
            ),
            json={"results": {"bindings": []}},
        )
        # BobOrg entity query — must NOT be requested thanks to the depth gate.
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(
                idref_queries.ORGANIZATION, "$organization", org2
            ),
            json={
                "results": {
                    "bindings": [
                        {"name": {"type": "literal", "value": "BobOrg"}},
                    ]
                }
            },
            is_optional=True,
        )

        response = await async_client.get(
            "/api/graph/",
            params={"root": self.ALICE, "type": "person", "depth": 2},
        )
        assert response.status_code == 200
        data = response.json()
        labels = {n["label"] for n in data["nodes"]}
        assert "Bob" in labels
        assert "BobOrg" not in labels
        assert len(data["nodes"]) == 3

    @pytest.mark.asyncio
    async def test_role_captured(self, async_client, httpx_mock):
        """Person→publication edge carries the ?role value from contributions."""
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(idref_queries.PERSON, "$person", self.ALICE),
            json={
                "results": {
                    "bindings": [
                        {"name": {"type": "literal", "value": "Alice"}},
                    ]
                }
            },
        )
        # Contributions query includes a role binding.
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(
                idref_queries.PERSON_CONTRIBUTIONS, "$person", self.ALICE
            ),
            json={
                "results": {
                    "bindings": [
                        {
                            "doc": {"type": "uri", "value": self.PUB1},
                            "role": {"type": "literal", "value": "author"},
                        },
                    ]
                }
            },
        )
        # Publication entity query.
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(
                idref_queries.PUBLICATION, "$publication", self.PUB1
            ),
            json={
                "results": {
                    "bindings": [
                        {"title": {"type": "literal", "value": "My Paper"}},
                    ]
                }
            },
        )

        response = await async_client.get(
            "/api/graph/",
            params={"root": self.ALICE, "type": "person", "depth": 1},
        )
        assert response.status_code == 200
        data = response.json()
        assert any(e["type"] == "author" for e in data["edges"])

    @pytest.mark.asyncio
    async def test_coauthor_edge_and_self_loop_filter(self, async_client, httpx_mock):
        """Co-author spec yields a coAuthorOf edge; the root self-loop is filtered."""
        bob = "http://www.idref.fr/bob/id"

        # Root person entity query.
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(idref_queries.PERSON, "$person", self.ALICE),
            json={
                "results": {
                    "bindings": [
                        {"name": {"type": "literal", "value": "Alice"}},
                    ]
                }
            },
        )
        # Contributions: one doc, the root as a (self) author, plus a distinct co-author.
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(
                idref_queries.PERSON_CONTRIBUTIONS, "$person", self.ALICE
            ),
            json={
                "results": {
                    "bindings": [
                        {
                            "doc": {"type": "uri", "value": self.PUB1},
                            "author": {"type": "uri", "value": self.ALICE},
                            "author_name": {"type": "literal", "value": "Alice"},
                        },
                        {
                            "doc": {"type": "uri", "value": self.PUB1},
                            "author": {"type": "uri", "value": bob},
                            "author_name": {"type": "literal", "value": "Bob"},
                        },
                    ]
                }
            },
        )
        # Publication entity query.
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(
                idref_queries.PUBLICATION, "$publication", self.PUB1
            ),
            json={
                "results": {
                    "bindings": [
                        {"title": {"type": "literal", "value": "My Paper"}},
                    ]
                }
            },
        )
        # Co-author (Bob) person entity query.
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(idref_queries.PERSON, "$person", bob),
            json={
                "results": {
                    "bindings": [
                        {"name": {"type": "literal", "value": "Bob"}},
                    ]
                }
            },
        )

        response = await async_client.get(
            "/api/graph/",
            params={"root": self.ALICE, "type": "person", "depth": 1},
        )
        assert response.status_code == 200
        data = response.json()
        assert any(
            e["type"] == "coAuthorOf" and e["target"] == bob for e in data["edges"]
        )
        assert all(e["source"] != e["target"] for e in data["edges"])

    @pytest.mark.asyncio
    async def test_publication_doi_populated(self, async_client, httpx_mock):
        """Publication entity binds a doi, which is surfaced on the node."""
        # Publication entity query (with doi binding).
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(
                idref_queries.PUBLICATION, "$publication", self.PUB1
            ),
            json={
                "results": {
                    "bindings": [
                        {
                            "title": {"type": "literal", "value": "My Paper"},
                            "doi": {"type": "literal", "value": "10.1234/foo"},
                        },
                    ]
                }
            },
        )
        # Publication persons query.
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(
                idref_queries.PUBLICATION_PERSONS, "$publication", self.PUB1
            ),
            json={"results": {"bindings": []}},
        )
        # Publication organizations query.
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(
                idref_queries.PUBLICATION_ORGANIZATIONS, "$publication", self.PUB1
            ),
            json={"results": {"bindings": []}},
        )

        response = await async_client.get(
            "/api/graph/",
            params={"root": self.PUB1, "type": "publication", "depth": 1},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) == 1
        assert data["nodes"][0]["type"] == "publication"
        assert data["nodes"][0]["doi"] == "10.1234/foo"

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


class TestGraphTruncation:
    ALICE = "http://www.idref.fr/001/id"
    ORG1 = "http://www.idref.fr/org1/id"
    PUB1 = "http://www.idref.fr/pub1/id"

    @pytest.mark.asyncio
    async def test_max_nodes_truncates(self, async_client, httpx_mock):
        """Node cap skips the inline org edge and its neighbor."""
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(idref_queries.PERSON, "$person", self.ALICE),
            json={
                "results": {
                    "bindings": [
                        {
                            "name": {"type": "literal", "value": "Alice"},
                            "org": {"type": "uri", "value": self.ORG1},
                            "orgName": {"type": "literal", "value": "CNRS"},
                        },
                    ]
                }
            },
        )
        # Contributions query returns empty.
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(
                idref_queries.PERSON_CONTRIBUTIONS, "$person", self.ALICE
            ),
            json={"results": {"bindings": []}},
        )

        response = await async_client.get(
            "/api/graph/",
            params={
                "root": self.ALICE,
                "type": "person",
                "depth": 1,
                "max_nodes": 1,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) == 1
        assert data["nodes"][0]["label"] == "Alice"
        assert data["edges"] == []
        assert data["truncated"] is True

    @pytest.mark.asyncio
    async def test_max_edges_truncates(self, async_client, httpx_mock):
        """Edge cap admits the inline org edge and skips the author edge."""
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(idref_queries.PERSON, "$person", self.ALICE),
            json={
                "results": {
                    "bindings": [
                        {
                            "name": {"type": "literal", "value": "Alice"},
                            "org": {"type": "uri", "value": self.ORG1},
                            "orgName": {"type": "literal", "value": "CNRS"},
                        },
                    ]
                }
            },
        )
        # Contributions query returns one publication (author edge).
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(
                idref_queries.PERSON_CONTRIBUTIONS, "$person", self.ALICE
            ),
            json={
                "results": {
                    "bindings": [
                        {
                            "doc": {"type": "uri", "value": self.PUB1},
                            "role": {"type": "literal", "value": "author"},
                        },
                    ]
                }
            },
        )
        # Org entity query (the inline org is enqueued at depth 1).
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(
                idref_queries.ORGANIZATION, "$organization", self.ORG1
            ),
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
                "root": self.ALICE,
                "type": "person",
                "depth": 1,
                "max_edges": 1,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["edges"]) <= 1
        assert data["truncated"] is True

    @pytest.mark.asyncio
    async def test_within_limits_not_truncated(self, async_client, httpx_mock):
        """A small graph under the default caps is not truncated."""
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(idref_queries.PERSON, "$person", self.ALICE),
            json={
                "results": {
                    "bindings": [
                        {"name": {"type": "literal", "value": "Alice"}},
                    ]
                }
            },
        )
        # Contributions query returns empty.
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(
                idref_queries.PERSON_CONTRIBUTIONS, "$person", self.ALICE
            ),
            json={"results": {"bindings": []}},
        )

        response = await async_client.get(
            "/api/graph/",
            params={
                "root": self.ALICE,
                "type": "person",
                "depth": 1,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["truncated"] is False


class TestGraphContinuation:
    ALICE = "http://www.idref.fr/001/id"
    ORG1 = "http://www.idref.fr/org1/id"
    BOB = "http://www.idref.fr/bob/id"

    def _params(self, continuation: str | None = None) -> dict:
        params = {
            "root": self.ALICE,
            "type": "person",
            "depth": 2,
            "max_nodes": 1,
        }
        if continuation is not None:
            params["continuation"] = continuation
        return params

    def _mock_person_alice(self, httpx_mock):
        """Root person entity query with an inline org."""
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(idref_queries.PERSON, "$person", self.ALICE),
            json={
                "results": {
                    "bindings": [
                        {
                            "name": {"type": "literal", "value": "Alice"},
                            "org": {"type": "uri", "value": self.ORG1},
                            "orgName": {"type": "literal", "value": "CNRS"},
                        },
                    ]
                }
            },
        )

    def _mock_contributions_empty(self, httpx_mock):
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(
                idref_queries.PERSON_CONTRIBUTIONS, "$person", self.ALICE
            ),
            json={"results": {"bindings": []}},
        )

    def _mock_org(self, httpx_mock):
        """ORG1 entity + members (Bob) + publications (empty)."""
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(
                idref_queries.ORGANIZATION, "$organization", self.ORG1
            ),
            json={
                "results": {
                    "bindings": [
                        {"name": {"type": "literal", "value": "CNRS"}},
                    ]
                }
            },
        )
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(
                idref_queries.ORGANIZATION_MEMBERS, "$organization", self.ORG1
            ),
            json={
                "results": {
                    "bindings": [
                        {
                            "person": {"type": "uri", "value": self.BOB},
                            "name": {"type": "literal", "value": "Bob"},
                        },
                    ]
                }
            },
        )
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(
                idref_queries.ORGANIZATION_PUBLICATIONS, "$organization", self.ORG1
            ),
            json={"results": {"bindings": []}},
        )

    def _mock_person_bob(self, httpx_mock):
        httpx_mock.add_response(
            url=SPARQL_ENDPOINT,
            method="POST",
            match_content=_query_body(idref_queries.PERSON, "$person", self.BOB),
            json={
                "results": {
                    "bindings": [
                        {"name": {"type": "literal", "value": "Bob"}},
                    ]
                }
            },
        )

    @pytest.mark.asyncio
    async def test_truncated_response_returns_continuation_id(
        self, async_client, httpx_mock
    ):
        """A fresh request that truncates returns a continuation id."""
        self._mock_person_alice(httpx_mock)
        self._mock_contributions_empty(httpx_mock)

        response = await async_client.get("/api/graph/", params=self._params())
        assert response.status_code == 200
        data = response.json()
        assert data["truncated"] is True
        assert data["continuation_id"] is not None

    @pytest.mark.asyncio
    async def test_continuation_returns_new_nodes_and_edges(
        self, async_client, httpx_mock
    ):
        """The next chunk only contains nodes/edges not already returned."""
        self._mock_person_alice(httpx_mock)
        self._mock_contributions_empty(httpx_mock)
        self._mock_org(httpx_mock)

        first = await async_client.get("/api/graph/", params=self._params())
        assert first.status_code == 200
        chunk1 = first.json()
        assert chunk1["continuation_id"] is not None

        second = await async_client.get(
            "/api/graph/", params=self._params(chunk1["continuation_id"])
        )
        assert second.status_code == 200
        chunk2 = second.json()

        assert len(chunk2["nodes"]) > 0
        assert len(chunk2["edges"]) > 0

        chunk1_nodes = {n["id"] for n in chunk1["nodes"]}
        chunk2_nodes = {n["id"] for n in chunk2["nodes"]}
        assert chunk1_nodes.isdisjoint(chunk2_nodes)

        chunk1_edges = {(e["source"], e["target"], e["type"]) for e in chunk1["edges"]}
        chunk2_edges = {(e["source"], e["target"], e["type"]) for e in chunk2["edges"]}
        assert chunk1_edges.isdisjoint(chunk2_edges)

    @pytest.mark.asyncio
    async def test_continuation_terminates_when_not_truncated(
        self, async_client, httpx_mock
    ):
        """Chunks stitch together the full graph and end with no continuation."""
        self._mock_person_alice(httpx_mock)
        self._mock_contributions_empty(httpx_mock)
        self._mock_org(httpx_mock)
        self._mock_person_bob(httpx_mock)

        node_ids: set[str] = set()
        edge_keys: set[tuple[str, str, str]] = set()
        total_nodes = 0
        total_edges = 0
        continuation: str | None = None
        chunks: list[dict] = []

        for _ in range(10):
            response = await async_client.get(
                "/api/graph/", params=self._params(continuation)
            )
            assert response.status_code == 200
            data = response.json()
            chunks.append(data)
            total_nodes += len(data["nodes"])
            total_edges += len(data["edges"])
            node_ids.update(n["id"] for n in data["nodes"])
            edge_keys.update(
                (e["source"], e["target"], e["type"]) for e in data["edges"]
            )
            if not data["truncated"]:
                assert data["continuation_id"] is None
                break
            assert data["continuation_id"] is not None
            continuation = data["continuation_id"]
        else:
            pytest.fail("traversal did not terminate within 10 chunks")

        # No duplicate node ids or edge keys across chunks.
        assert len(node_ids) == total_nodes
        assert len(edge_keys) == total_edges

        assert node_ids == {self.ALICE, self.ORG1, self.BOB}
        assert edge_keys == {
            (self.ALICE, self.ORG1, "affiliatedWith"),
            (self.ORG1, self.BOB, "memberOf"),
        }

    @pytest.mark.asyncio
    async def test_unknown_continuation_returns_404(self, async_client, httpx_mock):
        """An unknown or expired continuation id yields 404."""
        response = await async_client.get(
            "/api/graph/", params=self._params("does-not-exist")
        )
        assert response.status_code == 404
