# src/fetchers/archive_fetcher.py
import aiohttp
import asyncio
from typing import Optional

# On limite à 1000 snapshots pour accélérer la requête
# (le score est plafonné à 1000, donc on ne perd pas d'information)
ARCHIVE_URL = "https://web.archive.org/cdx/search/cdx?url={domain}/*&output=json&limit=1000&fl=timestamp"

async def get_archive_snapshot_count(domain: str, session: aiohttp.ClientSession) -> Optional[int]:
    url = ARCHIVE_URL.format(domain=domain)
    headers = {"User-Agent": "DomainScorer-MVP/1.0"}

    for attempt in range(2):
        try:
            # Timeout augmenté à 10 secondes pour laisser le temps à Archive
            timeout = aiohttp.ClientTimeout(total=10.0)
            async with session.get(url, headers=headers, timeout=timeout) as resp:
                if resp.status == 404:
                    return None
                if resp.status != 200:
                    if attempt == 0:
                        await asyncio.sleep(0.5)
                        continue
                    return None
                data = await resp.json()
                if not data or len(data) < 2:
                    return None
                # On retourne le nombre de snapshots (plafonné à 1000)
                return len(data) - 1
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
            if attempt == 0:
                await asyncio.sleep(0.5)
                continue
            return None
    return None