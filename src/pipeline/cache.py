# src/pipeline/cache.py - Version avec rafraîchissement forcé
from src.core.models import Result

_memory_cache = {}
CACHE_VERSION = "v1"

def _cache_key(domain: str) -> str:
    return f"domain:{domain}:{CACHE_VERSION}"

async def get_cached_result(domain: str):
    key = _cache_key(domain)
    return _memory_cache.get(key)

async def set_cached_result(result: Result) -> None:
    key = _cache_key(result.domain)
    _memory_cache[key] = result

async def clear_cache(domain: str = None):
    """Force le rafraîchissement du cache pour un domaine ou tout le cache."""
    if domain:
        key = _cache_key(domain)
        _memory_cache.pop(key, None)
    else:
        _memory_cache.clear()