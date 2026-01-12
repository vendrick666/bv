"""
Unit тесты (Занятие 18)
"""

from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_token,
)


class TestSecurity:
    def test_password_hash(self):
        password = "Test1234"
        hashed = get_password_hash(password)
        assert hashed != password
        assert verify_password(password, hashed)

    def test_password_wrong(self):
        hashed = get_password_hash("Test1234")
        assert not verify_password("Wrong123", hashed)

    def test_jwt_token(self):
        token = create_access_token({"sub": "123"})
        payload = decode_token(token)
        assert payload["sub"] == "123"
        assert payload["type"] == "access"

    def test_invalid_token(self):
        payload = decode_token("invalid.token.here")
        assert payload is None
