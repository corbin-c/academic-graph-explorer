import pytest


class TestGraphTraversal:
    @pytest.mark.asyncio
    async def test_traverse_with_minimal_params(self, async_client):
        response = await async_client.get(
            "/api/graph/", params={"root": "http://www.idref.fr/001/id"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["params"]["root"] == "http://www.idref.fr/001/id"

    @pytest.mark.asyncio
    async def test_traverse_with_all_params(self, async_client):
        response = await async_client.get(
            "/api/graph/",
            params={
                "root": "http://www.idref.fr/001/id",
                "depth": 3,
                "limit": 50,
                "relations": "authorOf,cites",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["params"]["depth"] == 3
        assert data["params"]["limit"] == 50
        assert data["params"]["relations"] == ["authorOf", "cites"]

    @pytest.mark.asyncio
    async def test_traverse_missing_root_returns_422(self, async_client):
        response = await async_client.get("/api/graph/")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_traverse_empty_root_returns_422(self, async_client):
        response = await async_client.get("/api/graph/", params={"root": ""})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_traverse_depth_out_of_range(self, async_client):
        # Depth 0 should fail (ge=1)
        response = await async_client.get(
            "/api/graph/",
            params={"root": "http://www.idref.fr/001/id", "depth": 0},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_default_depth_is_two(self, async_client):
        response = await async_client.get(
            "/api/graph/",
            params={"root": "http://www.idref.fr/001/id"},
        )
        assert response.status_code == 200
        assert response.json()["params"]["depth"] == 2
