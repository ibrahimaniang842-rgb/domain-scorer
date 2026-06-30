import asyncio
import logging
from typing import Optional

import aiohttp

from src.fetchers.http_utils import DEFAULT_HEADERS, FAST_TIMEOUT, fetch_with_retry

logger = logging.getLogger(__name__)

AHREFS_URL = "https://api.ahrefs.com/v3/public/domain-rating-free?target={domain}"
_ahrefs_semaphore = asyncio.Semaphore(8)


async def get_ahrefs_dr(domain: str, session: aiohttp.ClientSession) -> Optional[float]:
    url = AHREFS_URL.format(domain=domain)

    async def _request() -> Optional[float]:
        async with _ahrefs_semaphore:
            async with session.get(url, headers=DEFAULT_HEADERS, timeout=FAST_TIMEOUT) as resp:
                if resp.status == 404:
                    return 0.0
                if resp.status != 200:
                    raise aiohttp.ClientResponseError(
                        resp.request_info,
                        resp.history,
                        status=resp.status,
                        message=f"Ahrefs HTTP {resp.status}",
                    )
                data = await resp.json(content_type=None)
                dr = data.get("domain_rating", {}).get("domain_rating")
                if dr is None:
                    return 0.0
                dr_float = float(dr)
                return min(max(dr_float, 0.0), 100.0)

    result = await fetch_with_retry(_request, label=f"ahrefs:{domain}")
    return result
