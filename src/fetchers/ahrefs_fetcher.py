# src/fetchers/ahrefs_fetcher.py
import aiohttp
import asyncio
from typing import Optional

AHREFS_URL = "https://api.ahrefs.com/v3/public/domain-rating-free?target={domain}"
_ahrefs_semaphore = asyncio.Semaphore(10)

async def get_ahrefs_dr(domain: str, session: aiohttp.ClientSession) -> Optional[float]:
    url = AHREFS_URL.format(domain=domain)
    headers = {"User-Agent": "DomainScorer-MVP/1.0"}

    for attempt in range(2):
        try:
            timeout = aiohttp.ClientTimeout(total=4.0)
            async with _ahrefs_semaphore:
                async with session.get(url, headers=headers, timeout=timeout) as resp:
                    if resp.status == 404:
                        return None
                    if resp.status != 200:
                        if attempt == 0:
                            await asyncio.sleep(0.5)
                            continue
                        return None
                    data = await resp.json()
                    dr = data.get("domain_rating", {}).get("domain_rating")
                    if dr is None:
                        return None
                    try:
                        dr_float = float(dr)
                    except (ValueError, TypeError):
                        return None
                    dr_clamped = min(max(dr_float, 0.0), 100.0)
                    return dr_clamped
        except (aiohttp.ClientError, asyncio.TimeoutError):
            if attempt == 0:
                await asyncio.sleep(0.5)
                continue
            return None
    return None