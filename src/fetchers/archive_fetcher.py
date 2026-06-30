import logging
from typing import Any, Dict, Optional

import aiohttp

from src.fetchers.http_utils import ARCHIVE_TIMEOUT, DEFAULT_HEADERS, fetch_with_retry
from src.pipeline.cache import get_cached_archive_status, update_archive_history

logger = logging.getLogger(__name__)

ARCHIVE_URL = (
    "https://web.archive.org/cdx/search/cdx"
    "?url={domain}/*&output=json&limit=2&fl=timestamp&collapse=timestamp:8"
)


def _empty_result(status: str) -> Dict[str, Any]:
    return {
        "exists": False,
        "first_snapshot": None,
        "last_snapshot": None,
        "status": status,
    }


async def get_archive_status(domain: str, session: aiohttp.ClientSession) -> Dict[str, Any]:
    url = ARCHIVE_URL.format(domain=domain)

    async def _request() -> Dict[str, Any]:
        async with session.get(url, headers=DEFAULT_HEADERS, timeout=ARCHIVE_TIMEOUT) as resp:
            if resp.status != 200:
                return _empty_result("NO_DATA")

            data = await resp.json(content_type=None)
            if not data or len(data) < 2:
                return _empty_result("NO_DATA")

            timestamps = [row[0] for row in data[1:] if row and row[0]]
            if not timestamps:
                return _empty_result("NO_DATA")

            return {
                "exists": True,
                "first_snapshot": timestamps[0],
                "last_snapshot": timestamps[-1],
                "status": "OK",
            }

    result = await fetch_with_retry(_request, label=f"archive:{domain}")
    if result is None:
        cached = await get_cached_archive_status(domain)
        if cached:
            logger.info("[archive] recovered cached archive status for %s after timeout", domain)
            return cached
        return _empty_result("TIMEOUT")

    if result.get("status") == "OK" and result.get("exists"):
        await update_archive_history(domain, archive_status=result)

    return result
