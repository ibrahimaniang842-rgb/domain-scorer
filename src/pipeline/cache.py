import copy
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from src.core.models import Result, clone_result

_memory_cache: Dict[str, Tuple[float, Result]] = {}
_archive_history_cache: Dict[str, Tuple[float, "ArchiveHistoryEntry"]] = {}
CACHE_VERSION = "v3"
CACHE_TTL_SECONDS = 3600
ARCHIVE_HISTORY_TTL_SECONDS = 604800


@dataclass
class ArchiveHistoryEntry:
    archive_status: Optional[Dict[str, Any]] = None
    wayback_data: Optional[Dict[str, Any]] = None


def _normalize_domain(domain: str) -> str:
    return domain.lower().strip()


def _cache_key(domain: str) -> str:
    return f"domain:{_normalize_domain(domain)}:{CACHE_VERSION}"


def _archive_history_key(domain: str) -> str:
    return f"archive-history:{_normalize_domain(domain)}:{CACHE_VERSION}"


def _is_usable_archive_status(data: Dict[str, Any]) -> bool:
    return bool(data.get("exists")) and data.get("status") == "OK"


def _is_usable_wayback_data(data: Dict[str, Any]) -> bool:
    snapshots = data.get("snapshots") or []
    return len(snapshots) >= 1 and data.get("status") in {"OK", "PARTIAL"}


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


async def get_archive_history(domain: str) -> Optional[ArchiveHistoryEntry]:
    key = _archive_history_key(domain)
    entry = _archive_history_cache.get(key)
    if not entry:
        return None

    expires_at, history = entry
    if time.time() > expires_at:
        _archive_history_cache.pop(key, None)
        return None

    return copy.deepcopy(history)


async def update_archive_history(
    domain: str,
    *,
    archive_status: Optional[Dict[str, Any]] = None,
    wayback_data: Optional[Dict[str, Any]] = None,
) -> None:
    if archive_status is None and wayback_data is None:
        return

    key = _archive_history_key(domain)
    existing = await get_archive_history(domain) or ArchiveHistoryEntry()

    if archive_status is not None and _is_usable_archive_status(archive_status):
        existing.archive_status = copy.deepcopy(archive_status)

    if wayback_data is not None and _is_usable_wayback_data(wayback_data):
        existing.wayback_data = copy.deepcopy(wayback_data)

    if existing.archive_status is None and existing.wayback_data is None:
        return

    _archive_history_cache[key] = (
        time.time() + ARCHIVE_HISTORY_TTL_SECONDS,
        existing,
    )


async def get_cached_archive_status(domain: str) -> Optional[Dict[str, Any]]:
    history = await get_archive_history(domain)
    if history and history.archive_status:
        return copy.deepcopy(history.archive_status)
    return None


async def get_cached_wayback_data(domain: str) -> Optional[Dict[str, Any]]:
    history = await get_archive_history(domain)
    if history and history.wayback_data:
        return copy.deepcopy(history.wayback_data)
    return None


async def clear_cache(domain: Optional[str] = None) -> None:
    if domain:
        _memory_cache.pop(_cache_key(domain), None)
        _archive_history_cache.pop(_archive_history_key(domain), None)
    else:
        _memory_cache.clear()
        _archive_history_cache.clear()
