import copy
import time
from typing import Dict, Optional, Tuple

from src.core.models import Result, clone_result

_memory_cache: Dict[str, Tuple[float, Result]] = {}
CACHE_VERSION = "v2"
CACHE_TTL_SECONDS = 3600


def _cache_key(domain: str) -> str:
    return f"domain:{domain.lower().strip()}:{CACHE_VERSION}"


def _is_cacheable(result: Result) -> bool:
    if result.raw.data_quality == "FAILED":
        return False
    critical_missing = (
        result.raw.whois_age_days is None
        and result.raw.ahrefs_dr is None
        and result.raw.archive_status in {None, "ERROR", "TIMEOUT"}
    )
    return not critical_missing


async def get_cached_result(domain: str) -> Optional[Result]:
    key = _cache_key(domain)
    entry = _memory_cache.get(key)
    if not entry:
        return None

    expires_at, result = entry
    if time.time() > expires_at:
        _memory_cache.pop(key, None)
        return None

    return clone_result(result)


async def set_cached_result(result: Result) -> None:
    if not _is_cacheable(result):
        return
    key = _cache_key(result.domain)
    _memory_cache[key] = (time.time() + CACHE_TTL_SECONDS, clone_result(result))


async def clear_cache(domain: Optional[str] = None) -> None:
    if domain:
        _memory_cache.pop(_cache_key(domain), None)
    else:
        _memory_cache.clear()
