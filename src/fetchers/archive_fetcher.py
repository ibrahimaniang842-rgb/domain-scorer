# src/fetchers/archive_fetcher.py
import aiohttp
import asyncio
from typing import Optional

ARCHIVE_URL_LIGHT = "https://web.archive.org/cdx/search/cdx?url={domain}/*&output=json&limit=2&fl=timestamp"
TIMEOUT = 3.0

_cache = {}

async def get_archive_status(domain: str, session: aiohttp.ClientSession) -> dict:
    """
    Retourne :
    {
        "exists": bool,
        "first_snapshot": "YYYYMMDDHHMMSS" ou None,
        "last_snapshot": "YYYYMMDDHHMMSS" ou None,
        "status": "OK" | "NO_DATA" | "TIMEOUT" | "ERROR"
    }
    """
    if domain in _cache:
        return _cache[domain]

    url = ARCHIVE_URL_LIGHT.format(domain=domain)
    headers = {"User-Agent": "DomainScorer-MVP/1.0"}

    try:
        timeout = aiohttp.ClientTimeout(total=TIMEOUT)
        async with session.get(url, headers=headers, timeout=timeout) as resp:
            if resp.status != 200:
                result = {"exists": False, "first_snapshot": None, "last_snapshot": None, "status": "NO_DATA"}
                _cache[domain] = result
                return result
            data = await resp.json()
            if not data or len(data) < 2:
                result = {"exists": False, "first_snapshot": None, "last_snapshot": None, "status": "NO_DATA"}
                _cache[domain] = result
                return result
            timestamps = [row[0] for row in data[1:]]
            first = timestamps[0]
            last = timestamps[-1]
            result = {
                "exists": True,
                "first_snapshot": first,
                "last_snapshot": last,
                "status": "OK"
            }
            _cache[domain] = result
            return result
    except asyncio.TimeoutError:
        result = {"exists": False, "first_snapshot": None, "last_snapshot": None, "status": "TIMEOUT"}
        _cache[domain] = result
        return result
    except Exception:
        result = {"exists": False, "first_snapshot": None, "last_snapshot": None, "status": "ERROR"}
        _cache[domain] = result
        return result