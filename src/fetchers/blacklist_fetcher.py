import logging
import os
from typing import Any, Dict

import aiohttp

from src.fetchers.http_utils import FAST_TIMEOUT, fetch_with_retry

logger = logging.getLogger(__name__)

GOOGLE_SAFE_BROWSING_API_KEY = os.getenv("GOOGLE_SAFE_BROWSING_API_KEY", "")


def _unknown(reason: str) -> Dict[str, str]:
    return {"status": "UNKNOWN", "reason": reason}


async def get_blacklist_status(domain: str, session: aiohttp.ClientSession) -> Dict[str, str]:
    if not GOOGLE_SAFE_BROWSING_API_KEY:
        return _unknown("Clé API Google Safe Browsing manquante")

    url = f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={GOOGLE_SAFE_BROWSING_API_KEY}"
    payload = {
        "client": {"clientId": "domain-scorer", "clientVersion": "2.0.0"},
        "threatInfo": {
            "threatTypes": [
                "MALWARE",
                "SOCIAL_ENGINEERING",
                "UNWANTED_SOFTWARE",
                "POTENTIALLY_HARMFUL_APPLICATION",
            ],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": f"http://{domain}/"}],
        },
    }

    async def _request() -> Dict[str, str]:
        async with session.post(url, json=payload, timeout=FAST_TIMEOUT) as resp:
            if resp.status != 200:
                raise aiohttp.ClientResponseError(
                    resp.request_info,
                    resp.history,
                    status=resp.status,
                    message=f"SafeBrowsing HTTP {resp.status}",
                )
            data = await resp.json(content_type=None)
            matches = data.get("matches") or []
            if not matches:
                return {"status": "SAFE", "reason": "Aucune menace détectée"}
            threat_type = matches[0].get("threatType", "UNKNOWN")
            return {
                "status": threat_type,
                "reason": f"Blacklisté par Google Safe Browsing ({threat_type})",
            }

    result = await fetch_with_retry(_request, label=f"blacklist:{domain}")
    if result is None:
        return _unknown("Erreur de connexion à Google Safe Browsing")
    return result
