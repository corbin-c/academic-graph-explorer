import pytest


class TestSearch:
    @pytest.mark.asyncio
    async def test_search_with_query(self, async_client):
        response = await async_client.get("/api/search/", params={"q": "Dacos"})
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "Dacos"

    @pytest.mark.asyncio
    async def test_search_missing_query_returns_422(self, async_client):
        response = await async_client.get("/api/search/")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_search_empty_query_returns_422(self, async_client):
        response = await async_client.get("/api/search/", params={"q": ""})
        assert response.status_code == 422
