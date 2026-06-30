import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.fetchers.archive_fetcher import get_archive_status
from src.fetchers.http_utils import fetch_with_retry
from src.pipeline.cache import clear_cache, update_archive_history


@pytest.fixture(autouse=True)
async def reset_archive_cache():
    await clear_cache()
    yield
    await clear_cache()


@pytest.mark.asyncio
async def test_fetch_with_retry_succeeds_on_second_attempt():
    calls = {"count": 0}

    async def flaky():
        calls["count"] += 1
        if calls["count"] < 2:
            raise TimeoutError("temporary")
        return "ok"

    result = await fetch_with_retry(flaky, label="test", max_retries=3, backoff_base=0.01)
    assert result == "ok"
    assert calls["count"] == 2


@pytest.mark.asyncio
async def test_archive_fetcher_timeout_status():
    session = MagicMock()
    session.get = MagicMock(side_effect=TimeoutError())

    with patch("src.fetchers.archive_fetcher.fetch_with_retry", new=AsyncMock(return_value=None)):
        result = await get_archive_status("example.com", session)

    assert result["status"] == "TIMEOUT"
    assert result["exists"] is False


@pytest.mark.asyncio
async def test_archive_fetcher_recovers_from_cache_on_timeout():
    cached = {
        "exists": True,
        "first_snapshot": "20180101120000",
        "last_snapshot": "20240101120000",
        "status": "OK",
    }
    await update_archive_history("example.com", archive_status=cached)

    session = MagicMock()
    with patch("src.fetchers.archive_fetcher.fetch_with_retry", new=AsyncMock(return_value=None)):
        result = await get_archive_status("example.com", session)

    assert result["status"] == "OK"
    assert result["exists"] is True
    assert result["first_snapshot"] == "20180101120000"
