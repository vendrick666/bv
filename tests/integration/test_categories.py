import pytest


class TestCategoriesAPI:
    @pytest.mark.asyncio
    async def test_get_categories_empty(self, client):
        resp = await client.get("/api/v1/categories")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_create_category_requires_admin(self, client):
        resp = await client.post("/api/v1/categories", json={"name": "Тестовая"})
        assert resp.status_code == 401 or resp.status_code == 403

    @pytest.mark.asyncio
    async def test_create_and_get_categories(self, client, admin_headers):
        resp = await client.post(
            "/api/v1/categories",
            json={"name": "Тестовая", "description": "desc"},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Тестовая"

        resp2 = await client.get("/api/v1/categories")
        assert resp2.status_code == 200
        assert any(c["name"] == "Тестовая" for c in resp2.json())

    @pytest.mark.asyncio
    async def test_create_duplicate_fails(self, client, admin_headers):
        await client.post(
            "/api/v1/categories", json={"name": "DupCat"}, headers=admin_headers
        )
        resp = await client.post(
            "/api/v1/categories", json={"name": "DupCat"}, headers=admin_headers
        )
        assert resp.status_code == 400
