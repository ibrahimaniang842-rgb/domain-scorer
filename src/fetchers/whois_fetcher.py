import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

import aiohttp

from src.fetchers.http_utils import DEFAULT_HEADERS, FAST_TIMEOUT, fetch_with_retry

logger = logging.getLogger(__name__)

RDAP_URL = "https://rdap.org/domain/{domain}"


def _parse_rdap_date(value: str) -> Optional[datetime]:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _extract_creation_date(payload: dict) -> Optional[datetime]:
    events = payload.get("events") or []
    for event in events:
        action = (event.get("eventAction") or "").lower()
        if action in {"registration", "registered", "domain registration"}:
            parsed = _parse_rdap_date(event.get("eventDate", ""))
            if parsed:
                return parsed

    for key in ("registrationDate", "created", "creationDate"):
        if key in payload:
            parsed = _parse_rdap_date(str(payload[key]))
            if parsed:
                return parsed
    return None


def _days_since(creation_date: datetime) -> int:
    now = datetime.now(timezone.utc)
    return max(0, (now - creation_date).days)


async def _fetch_rdap_age(domain: str, session: aiohttp.ClientSession) -> Optional[int]:
    url = RDAP_URL.format(domain=domain)

    async def _request():
        async with session.get(url, headers=DEFAULT_HEADERS, timeout=FAST_TIMEOUT) as resp:
            if resp.status == 404:
                return None
            if resp.status != 200:
                raise aiohttp.ClientResponseError(
                    resp.request_info,
                    resp.history,
                    status=resp.status,
                    message=f"RDAP HTTP {resp.status}",
                )
            data = await resp.json(content_type=None)
            creation = _extract_creation_date(data)
            if not creation:
                return None
            return _days_since(creation)

    return await fetch_with_retry(_request, label=f"rdap:{domain}")


async def get_whois_age(domain: str, session: Optional[aiohttp.ClientSession] = None) -> Optional[int]:
    owns_session = session is None
    if owns_session:
        session = aiohttp.ClientSession(timeout=FAST_TIMEOUT)

    try:
        return await asyncio.wait_for(_fetch_rdap_age(domain, session), timeout=8.0)
    except asyncio.TimeoutError:
        logger.warning("[whois] global timeout for %s", domain)
        return None
    finally:
        if owns_session:
            await session.close()
