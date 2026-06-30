import pytest
from unittest.mock import AsyncMock, patch

from src.pipeline.orchestrator import score_domain


@pytest.mark.asyncio
async def test_orchestrator_marks_partial_on_archive_timeout():
    with patch("src.pipeline.orchestrator.get_whois_age", new=AsyncMock(return_value=1200)), \
         patch("src.pipeline.orchestrator.get_ahrefs_dr", new=AsyncMock(return_value=35.0)), \
         patch("src.pipeline.orchestrator.get_blacklist_status", new=AsyncMock(return_value={"status": "SAFE", "reason": "ok"})), \
         patch("src.pipeline.orchestrator.get_archive_status", new=AsyncMock(return_value={
             "exists": False,
             "first_snapshot": None,
             "last_snapshot": None,
             "status": "TIMEOUT",
         })), \
         patch("src.pipeline.orchestrator.get_wayback_snapshots", new=AsyncMock(return_value={
             "status": "TIMEOUT",
             "snapshots": [],
             "years_covered": [],
             "total_available": 0,
         })), \
         patch("src.pipeline.orchestrator.get_cached_result", new=AsyncMock(return_value=None)), \
         patch("src.pipeline.orchestrator.set_cached_result", new=AsyncMock()):

        result = await score_domain("example.com", use_archive=True)

    assert result.raw.data_quality == "PARTIAL"
    assert result.raw.archive_status == "TIMEOUT"
    assert result.raw.niche_shift["analysis_status"] == "TIMEOUT"
    assert result.raw.niche_shift["shift_detected"] is False


@pytest.mark.asyncio
async def test_orchestrator_does_not_invent_niche_on_timeout():
    with patch("src.pipeline.orchestrator.get_whois_age", new=AsyncMock(return_value=500)), \
         patch("src.pipeline.orchestrator.get_ahrefs_dr", new=AsyncMock(return_value=10.0)), \
         patch("src.pipeline.orchestrator.get_blacklist_status", new=AsyncMock(return_value={"status": "SAFE", "reason": "ok"})), \
         patch("src.pipeline.orchestrator.get_archive_status", new=AsyncMock(return_value={
             "exists": True,
             "first_snapshot": "20180101120000",
             "last_snapshot": "20200101120000",
             "status": "OK",
         })), \
         patch("src.pipeline.orchestrator.get_wayback_snapshots", new=AsyncMock(return_value={
             "status": "TIMEOUT",
             "snapshots": [],
             "years_covered": [],
             "total_available": 0,
         })), \
         patch("src.pipeline.orchestrator.get_cached_result", new=AsyncMock(return_value=None)), \
         patch("src.pipeline.orchestrator.set_cached_result", new=AsyncMock()):

        result = await score_domain("example.com")

    assert result.raw.niche_shift["history"] == []
    assert "timeout" in result.raw.niche_shift["shift_message"].lower()


@pytest.mark.asyncio
async def test_orchestrator_fictitious_domain_low_signals():
    with patch("src.pipeline.orchestrator.get_whois_age", new=AsyncMock(return_value=None)), \
         patch("src.pipeline.orchestrator.get_ahrefs_dr", new=AsyncMock(return_value=0.0)), \
         patch("src.pipeline.orchestrator.get_blacklist_status", new=AsyncMock(return_value={"status": "SAFE", "reason": "ok"})), \
         patch("src.pipeline.orchestrator.get_archive_status", new=AsyncMock(return_value={
             "exists": False,
             "first_snapshot": None,
             "last_snapshot": None,
             "status": "NO_DATA",
         })), \
         patch("src.pipeline.orchestrator.get_wayback_snapshots", new=AsyncMock(return_value={
             "status": "NO_DATA",
             "snapshots": [],
             "years_covered": [],
             "total_available": 0,
         })), \
         patch("src.pipeline.orchestrator.get_cached_result", new=AsyncMock(return_value=None)), \
         patch("src.pipeline.orchestrator.set_cached_result", new=AsyncMock()):

        result = await score_domain("fake-domain-xyz-2026.com")

    assert result.scores.seo <= 1.0
    assert result.danger.level in {"RED", "YELLOW"}
