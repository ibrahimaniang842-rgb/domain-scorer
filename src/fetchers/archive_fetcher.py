# src/fetchers/archive_fetcher.py
import aiohttp
import asyncio
from typing import Optional, Tuple

ARCHIVE_URL = "https://web.archive.org/cdx/search/cdx?url={domain}/*&output=json&limit=1000&fl=timestamp"
TIMEOUT = 3.0

_cache = {}

async def get_archive_snapshot_count(domain: str, session: aiohttp.ClientSession) -> Tuple[Optional[int], str]:
    """
    Retourne (snapshot_count, status)
    status = "OK" / "NO_DATA" / "TIMEOUT" / "ERROR"
    """
    if domain in _cache:
        return _cache[domain]

    url = ARCHIVE_URL.format(domain=domain)
    headers = {"User-Agent": "DomainScorer-MVP/1.0"}

    try:
        timeout = aiohttp.ClientTimeout(total=TIMEOUT)
        async with session.get(url, headers=headers, timeout=timeout) as resp:
            if resp.status == 404:
                result = (None, "NO_DATA")
                _cache[domain] = result
                return result
            if resp.status != 200:
                result = (None, "ERROR")
                _cache[domain] = result
                return result
            data = await resp.json()
            if not data or len(data) < 2:
                result = (None, "NO_DATA")
                _cache[domain] = result
                return result
            count = len(data) - 1
            result = (count, "OK")
            _cache[domain] = result
            return result
    except asyncio.TimeoutError:
        result = (None, "TIMEOUT")
        _cache[domain] = result
        return result
    except Exception:
        result = (None, "ERROR")
        _cache[domain] = result
        return result