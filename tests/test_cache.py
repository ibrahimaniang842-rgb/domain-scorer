import pytest
from unittest.mock import AsyncMock, patch

from src.core.models import Danger, RawData, Result, Scores, Toxicity, clone_result
from src.pipeline.cache import (
    clear_cache,
    get_archive_history,
    get_cached_result,
    set_cached_result,
    update_archive_history,
)


@pytest.fixture(autouse=True)
async def reset_cache():
    await clear_cache()
    yield
    await clear_cache()


@pytest.mark.asyncio
async def test_cache_stores_deep_copy():
    result = Result(
        domain="example.com",
        raw=RawData(domain="example.com", ahrefs_dr=10.0, data_quality="COMPLETE"),
        scores=Scores(seo=50.0, monetization=40.0),
        danger=Danger(level="GREEN", reasons=["ok"]),
        toxicity=Toxicity(score=0, level="SAFE", reasons=[]),
    )
    await set_cached_result(result)
    cached = await get_cached_result("example.com")
    cached.scores.seo = 999.0
    cached2 = await get_cached_result("example.com")
    assert cached2.scores.seo == 50.0


@pytest.mark.asyncio
async def test_cache_skips_failed_quality():
    result = Result(
        domain="broken.com",
        raw=RawData(domain="broken.com", data_quality="FAILED"),
        scores=Scores(seo=0.0, monetization=0.0),
        danger=Danger(level="ERROR", reasons=[]),
        toxicity=Toxicity(score=0, level="UNKNOWN", reasons=[]),
    )
    await set_cached_result(result)
    assert await get_cached_result("broken.com") is None


@pytest.mark.asyncio
async def test_archive_history_cache_merges_sources():
    archive = {
        "exists": True,
        "first_snapshot": "20180101120000",
        "last_snapshot": "20240101120000",
        "status": "OK",
    }
    wayback = {
        "status": "OK",
        "snapshots": [
            {"timestamp": "20180101120000", "year": 2018, "text": "x" * 150},
            {"timestamp": "20240101120000", "year": 2024, "text": "y" * 150},
        ],
        "years_covered": [2018, 2024],
        "total_available": 10,
    }
    await update_archive_history("Example.COM", archive_status=archive)
    await update_archive_history("example.com", wayback_data=wayback)

    history = await get_archive_history("example.com")
    assert history.archive_status["first_snapshot"] == "20180101120000"
    assert len(history.wayback_data["snapshots"]) == 2


def test_clone_result_isolated():
    result = Result(
        domain="example.com",
        raw=RawData(domain="example.com", fetch_errors={"whois": "timeout"}),
        scores=Scores(seo=1.0, monetization=1.0),
        danger=Danger(level="GREEN", reasons=[]),
        toxicity=Toxicity(score=0, level="SAFE", reasons=[]),
    )
    cloned = clone_result(result)
    cloned.raw.fetch_errors["whois"] = "changed"
    assert result.raw.fetch_errors["whois"] == "timeout"
