import pytest


class TestGetEntity:
    @pytest.mark.asyncio
    async def test_get_entity_returns_stub(self, async_client):
        response = await async_client.get("/api/entities/123")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "123" in data["message"]

    @pytest.mark.asyncio
    async def test_get_entity_with_uri_id(self, async_client):
        response = await async_client.get(
            "/api/entities/http%3A%2F%2Fwww.idref.fr%2F139753753%2Fid"
        )
        assert response.status_code == 200


class TestEntityRelationships:
    @pytest.mark.asyncio
    async def test_get_relationships_returns_stub(self, async_client):
        response = await async_client.get("/api/entities/123/relationships")
        assert response.status_code == 200
        data = response.json()
        assert "Relationships" in data["message"]


class TestEntityContributions:
    @pytest.mark.asyncio
    async def test_get_contributions_returns_stub(self, async_client):
        response = await async_client.get("/api/entities/123/contributions")
        assert response.status_code == 200
        data = response.json()
        assert "Contributions" in data["message"]
