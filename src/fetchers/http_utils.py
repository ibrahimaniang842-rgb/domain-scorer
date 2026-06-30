import asyncio
import logging
from typing import Any, Callable, Optional, TypeVar

import aiohttp

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=12.0, connect=4.0, sock_read=8.0)
FAST_TIMEOUT = aiohttp.ClientTimeout(total=6.0, connect=3.0, sock_read=5.0)
ARCHIVE_TIMEOUT = aiohttp.ClientTimeout(total=10.0, connect=4.0, sock_read=8.0)
WAYBACK_CDX_TIMEOUT = aiohttp.ClientTimeout(total=15.0, connect=5.0, sock_read=12.0)
WAYBACK_SNAPSHOT_TIMEOUT = aiohttp.ClientTimeout(total=12.0, connect=4.0, sock_read=10.0)

DEFAULT_HEADERS = {
    "User-Agent": "DomainScorer/2.0 (+https://domain-scorer.app)",
    "Accept": "application/json, text/html, */*",
}

MAX_RETRIES = 3
BACKOFF_BASE = 0.6

T = TypeVar("T")


async def fetch_with_retry(
    operation: Callable[[], Any],
    *,
    label: str,
    max_retries: int = MAX_RETRIES,
    backoff_base: float = BACKOFF_BASE,
) -> Optional[T]:
    last_error: Optional[Exception] = None
    for attempt in range(max_retries):
        try:
            return await operation()
        except asyncio.TimeoutError as exc:
            last_error = exc
            logger.warning("[%s] timeout attempt %d/%d", label, attempt + 1, max_retries)
        except aiohttp.ClientError as exc:
            last_error = exc
            logger.warning("[%s] client error attempt %d/%d: %s", label, attempt + 1, max_retries, exc)
        except Exception as exc:
            last_error = exc
            logger.warning("[%s] error attempt %d/%d: %s", label, attempt + 1, max_retries, exc)

        if attempt < max_retries - 1:
            await asyncio.sleep(backoff_base * (2 ** attempt))

    logger.error("[%s] failed after %d attempts: %s", label, max_retries, last_error)
    return None
