import pytest


class TestAuthValidation:
    @pytest.mark.asyncio
    async def test_register_invalid_password_returns_validation_error(self, client):
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "weak@test.com",
                "username": "weakuser",
                "password": "weakpass",
            },
        )
        assert resp.status_code == 422
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "details" in data["error"] and "errors" in data["error"]["details"]
        # At least one of the error messages should mention password
        msgs = [e["message"].lower() for e in data["error"]["details"]["errors"]]
        assert any(
            "password" in m or "парол" in m or "заглав" in m or "цифр" in m
            for m in msgs
        )
