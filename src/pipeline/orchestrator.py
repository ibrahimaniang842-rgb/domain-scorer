# src/pipeline/orchestrator.py - Version avec timeouts explicites
import asyncio
import aiohttp
import logging
from src.core.models import RawData, Scores, Danger, Result
from src.fetchers.whois_fetcher import get_whois_age
from src.fetchers.ahrefs_fetcher import get_ahrefs_dr
from src.fetchers.archive_fetcher import get_archive_snapshot_count
from src.scoring.seo import compute_seo_score
from src.scoring.monetization import compute_monetization_score
from src.scoring.danger import compute_danger
from src.pipeline.cache import get_cached_result, set_cached_result

logger = logging.getLogger(__name__)

async def score_domain(domain: str) -> Result:
    # 1. Cache
    cached = await get_cached_result(domain)
    if cached:
        return cached

    # 2. Session HTTP avec timeout global
    timeout = aiohttp.ClientTimeout(total=12.0, connect=5.0, sock_read=8.0)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        
        # 3. Appels avec timeouts individuels
        async def fetch_with_timeout(coro, name):
            try:
                return await asyncio.wait_for(coro, timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning(f"Timeout sur {name} pour {domain}")
                return None
            except Exception as e:
                logger.warning(f"Erreur sur {name} pour {domain}: {e}")
                return None

        tasks = [
            fetch_with_timeout(get_whois_age(domain), "whois"),
            fetch_with_timeout(get_ahrefs_dr(domain, session), "ahrefs"),
            fetch_with_timeout(get_archive_snapshot_count(domain, session), "archive")
        ]
        
        # 4. Exécution en parallèle
        age, dr, archive = await asyncio.gather(*tasks)

        # 5. Construction des données
        raw = RawData(
            domain=domain,
            whois_age_days=age,
            ahrefs_dr=dr,
            archive_snapshot_count=archive
        )

        seo = compute_seo_score(raw)
        mono = compute_monetization_score(domain)
        danger = compute_danger(raw)

        result = Result(
            domain=domain,
            raw=raw,
            scores=Scores(seo=seo, monetization=mono),
            danger=danger,
            explanation=None
        )

        await set_cached_result(result)
        return result