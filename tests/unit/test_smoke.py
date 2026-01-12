import pytest

from app.main import health


@pytest.mark.asyncio
async def test_health_endpoint():
    assert await health() == {"status": "healthy"}
