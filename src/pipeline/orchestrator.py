import asyncio
import logging
from typing import Any, Dict, Optional

import aiohttp

from src.core.models import Danger, RawData, Result, Scores, Toxicity
from src.fetchers.ahrefs_fetcher import get_ahrefs_dr
from src.fetchers.archive_fetcher import get_archive_status
from src.fetchers.blacklist_fetcher import get_blacklist_status
from src.fetchers.http_utils import DEFAULT_TIMEOUT
from src.fetchers.whois_fetcher import get_whois_age
from src.fetchers.wayback_content_fetcher import get_wayback_snapshots
from src.pipeline.cache import (
    get_cached_archive_status,
    get_cached_result,
    get_cached_wayback_data,
    set_cached_result,
    update_archive_history,
)
from src.scoring.danger import compute_danger
from src.scoring.monetization import compute_monetization_score
from src.scoring.niche_analyzer import analyze_niche_history
from src.scoring.seo import compute_seo_score
from src.scoring.toxicity import compute_toxicity

logger = logging.getLogger(__name__)


def _niche_unavailable(message: str, status: str = "UNAVAILABLE") -> Dict[str, Any]:
    return {
        "history": [],
        "shift_detected": False,
        "shift_message": message,
        "confidence": 0,
        "analysis_status": status,
    }


async def _safe_fetch(coro, name: str, domain: str, fetch_errors: Dict[str, str]):
    try:
        return await asyncio.wait_for(coro, timeout=15.0)
    except asyncio.TimeoutError:
        fetch_errors[name] = "timeout"
        logger.warning("[%s] timeout for %s", name, domain)
        return None
    except Exception as exc:
        fetch_errors[name] = str(exc)
        logger.warning("[%s] error for %s: %s", name, domain, exc)
        return None


def _resolve_data_quality(fetch_errors: Dict[str, str], archive_status: Optional[str]) -> str:
    if fetch_errors.get("ahrefs") and fetch_errors.get("whois"):
        return "FAILED"
    if archive_status in {"TIMEOUT", "ERROR"} or fetch_errors.get("archive") == "timeout":
        return "PARTIAL"
    if fetch_errors:
        return "PARTIAL"
    return "COMPLETE"


def _archive_failure_status(status: Optional[str]) -> bool:
    return status in {"TIMEOUT", "ERROR"}


async def _resolve_wayback_result(domain: str, wb_result: Any) -> Optional[Dict[str, Any]]:
    if isinstance(wb_result, dict):
        status = wb_result.get("status")
        snapshots = wb_result.get("snapshots") or []
        if status == "OK" or (status == "PARTIAL" and snapshots):
            await update_archive_history(domain, wayback_data=wb_result)
            return wb_result
        if _archive_failure_status(status):
            cached = await get_cached_wayback_data(domain)
            if cached and cached.get("snapshots"):
                logger.info("[orchestrator] recovered wayback snapshots from cache for %s", domain)
                return cached
        return wb_result

    cached = await get_cached_wayback_data(domain)
    if cached and cached.get("snapshots"):
        logger.info("[orchestrator] recovered wayback snapshots from cache for %s", domain)
        return cached
    return None


async def score_domain(domain: str, use_archive: bool = True) -> Result:
    cached = await get_cached_result(domain)
    if cached:
        return cached

    fetch_errors: Dict[str, str] = {}

    async with aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT) as session:
        tasks = [
            _safe_fetch(get_whois_age(domain, session), "whois", domain, fetch_errors),
            _safe_fetch(get_ahrefs_dr(domain, session), "ahrefs", domain, fetch_errors),
            _safe_fetch(get_blacklist_status(domain, session), "blacklist", domain, fetch_errors),
        ]

        if use_archive:
            tasks.append(
                _safe_fetch(get_archive_status(domain, session), "archive", domain, fetch_errors)
            )
        else:
            tasks.append(asyncio.sleep(0, result=None))

        results = await asyncio.gather(*tasks)
        age = results[0]
        dr = results[1]
        blacklist_data = results[2]
        archive_data = results[3] if len(results) > 3 else None

        archive_exists = None
        archive_first_date = None
        archive_last_date = None
        archive_status = "SKIPPED" if not use_archive else "ERROR"

        if isinstance(archive_data, dict):
            archive_exists = archive_data.get("exists")
            archive_first_date = archive_data.get("first_snapshot")
            archive_last_date = archive_data.get("last_snapshot")
            archive_status = archive_data.get("status", "ERROR")
            if _archive_failure_status(archive_status):
                cached_archive = await get_cached_archive_status(domain)
                if cached_archive:
                    logger.info("[orchestrator] recovered archive status from cache for %s", domain)
                    archive_data = cached_archive
                    archive_exists = cached_archive.get("exists")
                    archive_first_date = cached_archive.get("first_snapshot")
                    archive_last_date = cached_archive.get("last_snapshot")
                    archive_status = cached_archive.get("status", "OK")
                    fetch_errors.pop("archive", None)
                else:
                    fetch_errors["archive"] = archive_status.lower()
            elif archive_status == "OK" and archive_exists:
                await update_archive_history(domain, archive_status=archive_data)
                fetch_errors.pop("archive", None)
        elif use_archive:
            cached_archive = await get_cached_archive_status(domain)
            if cached_archive:
                logger.info("[orchestrator] recovered archive status from cache for %s", domain)
                archive_exists = cached_archive.get("exists")
                archive_first_date = cached_archive.get("first_snapshot")
                archive_last_date = cached_archive.get("last_snapshot")
                archive_status = cached_archive.get("status", "OK")
                fetch_errors.pop("archive", None)

        blacklist_status = None
        blacklist_reason = None
        if isinstance(blacklist_data, dict):
            blacklist_status = blacklist_data.get("status")
            blacklist_reason = blacklist_data.get("reason")

        niche_history = None
        niche_shift = None

        if use_archive:
            wb_result = await _safe_fetch(
                get_wayback_snapshots(domain, session),
                "wayback",
                domain,
                fetch_errors,
            )
            wb_result = await _resolve_wayback_result(domain, wb_result)

            if isinstance(wb_result, dict):
                wb_status = wb_result.get("status")
                snapshots = wb_result.get("snapshots") or []
                if wb_status == "OK":
                    fetch_errors.pop("wayback", None)

                if _archive_failure_status(wb_status):
                    niche_shift = _niche_unavailable(
                        "Archive.org indisponible (timeout) — analyse de niche non effectuée",
                        status="TIMEOUT",
                    )
                elif wb_status == "NO_DATA" or len(snapshots) < 2:
                    niche_shift = _niche_unavailable(
                        "Historique Wayback insuffisant pour une analyse de niche fiable",
                        status="INSUFFICIENT",
                    )
                elif wb_status in {"OK", "PARTIAL"}:
                    niche_shift = analyze_niche_history(snapshots, whois_age_days=age)
                    niche_history = niche_shift.get("history", [])
                else:
                    niche_shift = _niche_unavailable(
                        "Analyse de niche indisponible",
                        status="ERROR",
                    )
            else:
                niche_shift = _niche_unavailable(
                    "Impossible de récupérer l'historique Wayback",
                    status="ERROR",
                )
        else:
            niche_shift = _niche_unavailable(
                "Analyse de niche désactivée (mode rapide)",
                status="SKIPPED",
            )

        data_quality = _resolve_data_quality(fetch_errors, archive_status)

        raw = RawData(
            domain=domain,
            whois_age_days=age,
            ahrefs_dr=dr,
            archive_exists=archive_exists,
            archive_first_date=archive_first_date,
            archive_last_date=archive_last_date,
            archive_status=archive_status,
            blacklist_status=blacklist_status,
            blacklist_reason=blacklist_reason,
            niche_history=niche_history,
            niche_shift=niche_shift,
            fetch_errors=fetch_errors,
            data_quality=data_quality,
        )

        seo = compute_seo_score(raw)
        mono = compute_monetization_score(domain)
        danger = compute_danger(raw)
        toxicity_data = compute_toxicity(raw)
        toxicity = Toxicity(
            score=toxicity_data["score"],
            level=toxicity_data["level"],
            reasons=toxicity_data["reasons"],
        )

        result = Result(
            domain=domain,
            raw=raw,
            scores=Scores(seo=seo, monetization=mono),
            danger=danger,
            toxicity=toxicity,
            explanation=None,
        )

        await set_cached_result(result)
        return result
