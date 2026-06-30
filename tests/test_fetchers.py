import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.fetchers.archive_fetcher import get_archive_status
from src.fetchers.http_utils import fetch_with_retry


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
