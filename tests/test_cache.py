import pytest

from src.core.models import Danger, RawData, Result, Scores, Toxicity, clone_result
from src.pipeline.cache import clear_cache, get_cached_result, set_cached_result


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
