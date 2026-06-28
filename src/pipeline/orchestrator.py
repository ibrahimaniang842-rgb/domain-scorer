# src/pipeline/orchestrator.py
import asyncio
import aiohttp
import logging
from src.core.models import RawData, Scores, Danger, Toxicity, Result
from src.fetchers.whois_fetcher import get_whois_age
from src.fetchers.ahrefs_fetcher import get_ahrefs_dr
from src.fetchers.archive_fetcher import get_archive_status
from src.fetchers.blacklist_fetcher import get_blacklist_status
from src.fetchers.wayback_content_fetcher import get_wayback_snapshots
from src.scoring.seo import compute_seo_score
from src.scoring.monetization import compute_monetization_score
from src.scoring.danger import compute_danger
from src.scoring.toxicity import compute_toxicity
from src.scoring.niche_analyzer import analyze_niche_history
from src.pipeline.cache import get_cached_result, set_cached_result

logger = logging.getLogger(__name__)

async def score_domain(domain: str, use_archive: bool = True) -> Result:
    cached = await get_cached_result(domain)
    if cached:
        return cached

    timeout = aiohttp.ClientTimeout(total=12.0, connect=5.0, sock_read=8.0)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async def safe_fetch(coro, name="unknown"):
            try:
                return await asyncio.wait_for(coro, timeout=10.0)
            except Exception as e:
                logger.warning(f"Erreur sur {name} pour {domain}: {e}")
                return None

        tasks = [
            safe_fetch(get_whois_age(domain), "whois"),
            safe_fetch(get_ahrefs_dr(domain, session), "ahrefs"),
            safe_fetch(get_blacklist_status(domain, session), "blacklist")
        ]
        if use_archive:
            tasks.append(safe_fetch(get_archive_status(domain, session), "archive"))
        else:
            tasks.append(asyncio.sleep(0, result=None))

        results = await asyncio.gather(*tasks)
        age = results[0]
        dr = results[1]
        blacklist_data = results[2] if len(results) > 2 else None

        # --- Gestion du nouveau format Archive ---
        archive_data = results[3] if len(results) > 3 else None
        if archive_data and isinstance(archive_data, dict):
            archive_exists = archive_data.get("exists")
            archive_first_date = archive_data.get("first_snapshot")
            archive_last_date = archive_data.get("last_snapshot")
            archive_status = archive_data.get("status")
        else:
            archive_exists = None
            archive_first_date = None
            archive_last_date = None
            archive_status = "ERROR"

        if blacklist_data and isinstance(blacklist_data, dict):
            blacklist_status = blacklist_data.get("status")
            blacklist_reason = blacklist_data.get("reason")
        else:
            blacklist_status = None
            blacklist_reason = None

        # --- Analyse sémantique Wayback (V1.4.3 intégré) ---
        niche_history = None
        niche_shift = None
        if use_archive:
            wb_result = await get_wayback_snapshots(domain, session)
            if wb_result and wb_result.get("status") == "OK":
                snapshots = wb_result.get("snapshots", [])
                if snapshots and len(snapshots) >= 2:
                    niche_shift = analyze_niche_history(snapshots)
                    niche_history = niche_shift.get("history", []) if niche_shift else []
                else:
                    niche_shift = {
                        "shift_detected": False,
                        "shift_message": "Snapshots récupérés mais insuffisants pour une analyse fiable",
                        "confidence": 0
                    }
            else:
                niche_shift = {
                    "shift_detected": False,
                    "shift_message": "Historique insuffisant pour analyser la niche (timeout ou indisponible)",
                    "confidence": 0
                }
        # --- FIN ANALYSE WAYBACK ---

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
            niche_shift=niche_shift
        )

        seo = compute_seo_score(raw)
        mono = compute_monetization_score(domain)
        danger = compute_danger(raw)
        toxicity_data = compute_toxicity(raw)
        toxicity = Toxicity(
            score=toxicity_data["score"],
            level=toxicity_data["level"],
            reasons=toxicity_data["reasons"]
        )

        result = Result(
            domain=domain,
            raw=raw,
            scores=Scores(seo=seo, monetization=mono),
            danger=danger,
            toxicity=toxicity,
            explanation=None
        )

        await set_cached_result(result)
        return result