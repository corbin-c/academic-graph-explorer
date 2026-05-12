"""Test SPARQL response caching."""

import json

import pytest
from httpx import URL


class TestCacheBehavior:
    @pytest.mark.asyncio
    async def test_person_result_is_cached_on_second_call(
        self, async_client, httpx_mock
    ):
        """Second call to the same person should use cached result (only one HTTP call)."""
        person_data = {
            "head": {"vars": ["name", "note", "org", "orgName"]},
            "results": {
                "bindings": [
                    {
                        "name": {"type": "literal", "value": "Test Person"},
                        "note": {"type": "literal", "value": "A note."},
                    }
                ]
            },
        }

        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json=person_data,
        )

        # First call — hits SPARQL, caches result
        response1 = await async_client.get("/api/person/000000001")
        assert response1.status_code == 200
        assert response1.json()["label"] == "Test Person"

        # Second call — should use cache, but httpx_mock still has the response
        # If caching works, only one SPARQL call was made across both requests
        response2 = await async_client.get("/api/person/000000001")
        assert response2.status_code == 200
        assert response2.json()["label"] == "Test Person"

        # Verify only one HTTP request was made (the second was cached)
        requests = httpx_mock.get_requests()
        assert len(requests) == 1

    @pytest.mark.asyncio
    async def test_different_queries_are_not_cached_together(
        self, async_client, httpx_mock
    ):
        """Different persons should generate separate cache entries."""
        person_a = {
            "head": {"vars": ["name", "note", "org", "orgName"]},
            "results": {
                "bindings": [{"name": {"type": "literal", "value": "Person A"}}]
            },
        }
        person_b = {
            "head": {"vars": ["name", "note", "org", "orgName"]},
            "results": {
                "bindings": [{"name": {"type": "literal", "value": "Person B"}}]
            },
        }

        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json=person_a,
        )

        response_a = await async_client.get("/api/person/000000001")
        assert response_a.json()["label"] == "Person A"
        assert len(httpx_mock.get_requests()) == 1

        # Switch mock to different response for different person
        httpx_mock.reset()
        httpx_mock.add_response(
            url="https://data.idref.fr/sparql",
            method="POST",
            json=person_b,
        )

        response_b = await async_client.get("/api/person/000000002")
        assert response_b.json()["label"] == "Person B"
        assert len(httpx_mock.get_requests()) == 1
