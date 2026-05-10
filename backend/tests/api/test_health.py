import pytest


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_returns_ok(self, async_client):
        response = await async_client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestRootEndpoint:
    @pytest.mark.asyncio
    async def test_root_returns_app_info(self, async_client):
        response = await async_client.get("/api")
        assert response.status_code == 200
        data = response.json()
        assert data["app"] == "Academic Graph Explorer API"
        assert "version" in data
