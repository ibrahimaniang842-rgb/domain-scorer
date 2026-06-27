# src/fetchers/blacklist_fetcher.py
import aiohttp
import os
from typing import Optional

GOOGLE_SAFE_BROWSING_API_KEY = os.getenv("GOOGLE_SAFE_BROWSING_API_KEY", "")

async def get_blacklist_status(domain: str, session: aiohttp.ClientSession) -> dict:
    if GOOGLE_SAFE_BROWSING_API_KEY == "":
        return {"status": "UNKNOWN", "reason": "Clé API manquante"}

    url = f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={GOOGLE_SAFE_BROWSING_API_KEY}"
    payload = {
        "client": {"clientId": "domain-scorer", "clientVersion": "1.0.0"},
        "threatInfo": {
            "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": f"http://{domain}"}]
        }
    }
    try:
        async with session.post(url, json=payload, timeout=10.0) as resp:
            if resp.status != 200:
                return {"status": "UNKNOWN", "reason": f"Erreur HTTP {resp.status}"}
            data = await resp.json()
            if "matches" not in data or not data["matches"]:
                return {"status": "SAFE", "reason": "Aucune menace détectée"}
            threat_type = data["matches"][0].get("threatType", "UNKNOWN")
            return {"status": threat_type, "reason": f"Blacklisté par Google Safe Browsing ({threat_type})"}
    except Exception:
        return {"status": "UNKNOWN", "reason": "Erreur de connexion à Safe Browsing"}