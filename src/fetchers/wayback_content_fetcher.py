import asyncio
import logging
import re
from typing import Dict, List, Optional, Tuple

import aiohttp
from bs4 import BeautifulSoup

from src.fetchers.http_utils import (
    DEFAULT_HEADERS,
    WAYBACK_CDX_TIMEOUT,
    WAYBACK_SNAPSHOT_TIMEOUT,
    fetch_with_retry,
)

logger = logging.getLogger(__name__)

_WAYBACK_SEMAPHORE = asyncio.Semaphore(3)
_MIN_TEXT_CHARS = 150

_WAYBACK_TOOLBAR_RE = re.compile(
    r"<!-- BEGIN WAYBACK TOOLBAR.*?<!-- END WAYBACK TOOLBAR -->",
    re.DOTALL | re.IGNORECASE,
)
_WAYBACK_SCRIPT_RE = re.compile(
    r"<script[^>]*>.*?archive\.org.*?</script>",
    re.DOTALL | re.IGNORECASE,
)
_PARKED_OR_404_RE = re.compile(
    r"(page not found|404 error|domain is for sale|buy this domain|ce domaine est en vente|"
    r"domain listed for sale|under construction|site en construction|this page cannot be displayed)",
    re.IGNORECASE,
)


def _clean_domain(domain: str) -> str:
    domain = domain.strip().lower()
    for prefix in ("https://", "http://", "www."):
        if domain.startswith(prefix):
            domain = domain[len(prefix):]
    return domain.split("/")[0]


def _result(status: str, snapshots: list, total: int, years: Optional[List[int]] = None) -> Dict:
    return {
        "status": status,
        "snapshots": snapshots,
        "years_covered": years or [],
        "total_available": total,
    }


async def get_wayback_snapshots(domain: str, session: aiohttp.ClientSession) -> Dict:
    cleaned_domain = _clean_domain(domain)
    timestamps = await _fetch_cdx_timestamps(cleaned_domain, session)

    if timestamps is None:
        return _result("TIMEOUT", [], 0)
    if not timestamps:
        return _result("NO_DATA", [], 0)

    selected = _select_by_year(timestamps, max_snapshots=5)
    logger.info(
        "[WAYBACK] %s -> %d snapshots selectionnes sur %d",
        cleaned_domain,
        len(selected),
        len(timestamps),
    )

    fetch_tasks = [_fetch_and_clean(cleaned_domain, ts, session) for ts in selected]
    raw_results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

    snapshots = []
    for ts, result in zip(selected, raw_results):
        if isinstance(result, Exception):
            logger.debug("[WAYBACK] snapshot %s failed: %s", ts, result)
            continue
        if result is None:
            continue
        text, year = result
        snapshots.append({"timestamp": ts, "year": year, "text": text})

    years_covered = sorted({s["year"] for s in snapshots if s["year"]})
    status = "OK" if len(snapshots) >= 2 else ("PARTIAL" if snapshots else "NO_DATA")
    return _result(status, snapshots, len(timestamps), years_covered)


async def _fetch_cdx_timestamps(domain: str, session: aiohttp.ClientSession) -> Optional[List[str]]:
    cdx_url = (
        f"https://web.archive.org/cdx/search/cdx"
        f"?url={domain}/*&output=json&limit=50&fl=timestamp&collapse=timestamp:6"
    )

    async def _request() -> List[str]:
        async with _WAYBACK_SEMAPHORE:
            async with session.get(cdx_url, headers=DEFAULT_HEADERS, timeout=WAYBACK_CDX_TIMEOUT) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json(content_type=None)
                if not data or len(data) < 2:
                    return []
                return [row[0] for row in data[1:] if row and row[0]]

    result = await fetch_with_retry(_request, label=f"wayback-cdx:{domain}")
    if result is None:
        return None
    return result


def _select_by_year(timestamps: List[str], max_snapshots: int = 5) -> List[str]:
    by_year: Dict[int, List[str]] = {}
    for ts in timestamps:
        if len(ts) >= 4:
            try:
                year = int(ts[:4])
                by_year.setdefault(year, []).append(ts)
            except ValueError:
                continue

    if not by_year:
        indices = _spread_indices(len(timestamps), max_snapshots)
        return [timestamps[i] for i in indices if i < len(timestamps)]

    years_sorted = sorted(by_year.keys())
    one_per_year = []
    for year in years_sorted:
        year_ts = sorted(by_year[year])
        one_per_year.append(year_ts[len(year_ts) // 2])

    if len(one_per_year) <= max_snapshots:
        return one_per_year

    indices = _spread_indices(len(one_per_year), max_snapshots)
    return [one_per_year[i] for i in indices]


def _spread_indices(n: int, k: int) -> List[int]:
    if n <= 0:
        return []
    if k >= n:
        return list(range(n))
    if k == 1:
        return [n // 2]
    step = (n - 1) / (k - 1)
    return [round(step * i) for i in range(k)]


async def _fetch_and_clean(domain: str, timestamp: str, session: aiohttp.ClientSession) -> Optional[Tuple[str, int]]:
    html = await _fetch_raw_html(domain, timestamp, session)
    if html is None:
        return None

    text = _extract_clean_text(html)
    if not text or len(text) < _MIN_TEXT_CHARS:
        return None
    if _PARKED_OR_404_RE.search(text):
        return None

    try:
        year = int(timestamp[:4])
    except (ValueError, IndexError):
        return None

    return text, year


async def _fetch_raw_html(domain: str, timestamp: str, session: aiohttp.ClientSession) -> Optional[str]:
    url = f"https://web.archive.org/web/{timestamp}id_/{domain}"

    async def _request() -> Optional[str]:
        async with _WAYBACK_SEMAPHORE:
            async with session.get(
                url,
                headers=DEFAULT_HEADERS,
                timeout=WAYBACK_SNAPSHOT_TIMEOUT,
                allow_redirects=True,
            ) as resp:
                if resp.status != 200:
                    return None
                raw_bytes = await resp.read()
                return _decode_bytes(raw_bytes, resp)

    return await fetch_with_retry(_request, label=f"wayback-snap:{domain}:{timestamp}")


def _decode_bytes(raw: bytes, resp: aiohttp.ClientResponse) -> str:
    declared = resp.charset
    if declared:
        try:
            return raw.decode(declared, errors="replace")
        except (LookupError, UnicodeDecodeError):
            pass
    try:
        head = raw[:2000].decode("ascii", errors="ignore")
        match = re.search(r'charset=["\']?([\w-]+)', head, re.IGNORECASE)
        if match:
            return raw.decode(match.group(1).lower(), errors="replace")
    except Exception:
        pass
    for enc in ("utf-8", "windows-1252", "iso-8859-1", "latin-1"):
        try:
            return raw.decode(enc, errors="strict")
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")


def _extract_clean_text(html: str) -> str:
    html = _WAYBACK_TOOLBAR_RE.sub("", html)
    html = _WAYBACK_SCRIPT_RE.sub("", html)
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception:
        return ""
    for tag in soup(["script", "style", "noscript", "iframe", "head", "meta", "link"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()
