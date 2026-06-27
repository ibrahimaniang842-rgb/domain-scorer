# src/pipeline/orchestrator.py
import asyncio
import aiohttp
import logging
from src.core.models import RawData, Scores, Danger, Toxicity, Result
from src.fetchers.whois_fetcher import get_whois_age
from src.fetchers.ahrefs_fetcher import get_ahrefs_dr
from src.fetchers.archive_fetcher import get_archive_snapshot_count
from src.fetchers.blacklist_fetcher import get_blacklist_status
from src.scoring.seo import compute_seo_score
from src.scoring.monetization import compute_monetization_score
from src.scoring.danger import compute_danger
from src.scoring.toxicity import compute_toxicity
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
            tasks.append(safe_fetch(get_archive_snapshot_count(domain, session), "archive"))
        else:
            tasks.append(asyncio.sleep(0, result=None))

        results = await asyncio.gather(*tasks)
        age = results[0]
        dr = results[1]
        blacklist_data = results[2] if len(results) > 2 else None

        # Gestion du résultat Archive
        archive_result = results[3] if len(results) > 3 else None
        if archive_result and isinstance(archive_result, tuple):
            archive_count, archive_status = archive_result
        else:
            archive_count = None
            archive_status = "ERROR"

        if blacklist_data and isinstance(blacklist_data, dict):
            blacklist_status = blacklist_data.get("status")
            blacklist_reason = blacklist_data.get("reason")
        else:
            blacklist_status = None
            blacklist_reason = None

        raw = RawData(
            domain=domain,
            whois_age_days=age,
            ahrefs_dr=dr,
            archive_snapshot_count=archive_count,
            archive_status=archive_status,
            blacklist_status=blacklist_status,
            blacklist_reason=blacklist_reason
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