"""
Integration тесты API (Занятие 19)
"""

import pytest
from httpx import AsyncClient


class TestAuth:
    @pytest.mark.asyncio
    async def test_register(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "new@test.com",
                "username": "newuser",
                "password": "Test1234",
            },
        )
        assert response.status_code == 201
        assert response.json()["email"] == "new@test.com"

    @pytest.mark.asyncio
    async def test_login(self, client: AsyncClient, test_user):
        response = await client.post(
            "/api/v1/auth/login",
            json={
                # Changed from "email" to "login" to match LoginRequest schema
                "login": "test@test.com",
                "password": "Test1234",
            },
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, test_user):
        response = await client.post(
            "/api/v1/auth/login",
            json={
                # Changed from "email" to "login" to match LoginRequest schema
                "login": "test@test.com",
                "password": "Wrong123",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_me(self, client: AsyncClient, auth_headers):
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["email"] == "test@test.com"


class TestItems:
    @pytest.mark.asyncio
    async def test_get_items_empty(self, client: AsyncClient):
        response = await client.get("/api/v1/items")
        assert response.status_code == 200
        assert response.json()["items"] == []

    @pytest.mark.asyncio
    async def test_create_item_unauthorized(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/items",
            json={
                "name": "Test",
                "price": "100.00",
            },
        )
        # Should return 401 (Unauthorized) when no token provided,
        # or 403 (Forbidden) when token is provided but insufficient permissions
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_create_item_as_seller(self, client: AsyncClient, seller_headers):
        response = await client.post(
            "/api/v1/items",
            json={
                "name": "Test Parfume",
                "price": "150.00",
                "brand": "Test Brand",
                "volume_ml": 50,
            },
            headers=seller_headers,
        )
        assert response.status_code == 201
        assert response.json()["name"] == "Test Parfume"


class TestCart:
    @pytest.mark.asyncio
    async def test_get_empty_cart(self, client: AsyncClient, auth_headers):
        response = await client.get("/api/v1/cart", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["items"] == []


class TestHealth:
    @pytest.mark.asyncio
    async def test_health(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
