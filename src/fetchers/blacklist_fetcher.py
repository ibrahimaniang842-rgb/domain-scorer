# src/fetchers/blacklist_fetcher.py
import aiohttp
import json
from typing import Optional

# ⚠️ À remplacer par ta clé API Google Safe Browsing
# Pour une meilleure sécurité, mets-la dans une variable d'environnement plus tard
GOOGLE_SAFE_BROWSING_API_KEY = "AIzaSyB1-RUCkQd10_TdNc3-uF2P6ozR4f9Ktpk"

async def get_blacklist_status(domain: str, session: aiohttp.ClientSession) -> dict:
    """
    Vérifie si un domaine est blacklisté par Google Safe Browsing.
    Retourne : {"status": "SAFE"} ou {"status": "MALWARE", "reason": "..."}
    """
    if GOOGLE_SAFE_BROWSING_API_KEY == "YOUR_API_KEY_HERE":
        # Pas de clé configurée → on considère comme SAFE (neutre)
        return {"status": "UNKNOWN", "reason": "Clé API manquante"}

    url = f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={GOOGLE_SAFE_BROWSING_API_KEY}"
    
    payload = {
        "client": {
            "clientId": "domain-scorer",
            "clientVersion": "1.0.0"
        },
        "threatInfo": {
            "threatTypes": [
                "MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE",
                "POTENTIALLY_HARMFUL_APPLICATION"
            ],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": f"http://{domain}"}]
        }
    }

    try:
        async with session.post(url, json=payload, timeout=5.0) as resp:
            if resp.status != 200:
                # Erreur API ou quota dépassé → on ne bloque pas le pipeline
                return {"status": "UNKNOWN", "reason": f"Erreur HTTP {resp.status}"}
            
            data = await resp.json()
            
            # Si la réponse ne contient pas "matches", le domaine est SAFE
            if "matches" not in data or not data["matches"]:
                return {"status": "SAFE", "reason": "Aucune menace détectée"}
            
            # On extrait le premier type de menace trouvé
            threat_type = data["matches"][0].get("threatType", "UNKNOWN")
            return {
                "status": threat_type,
                "reason": f"Blacklisté par Google Safe Browsing ({threat_type})"
            }
            
    except (aiohttp.ClientError, TimeoutError):
        # Timeout ou erreur réseau → on ne bloque pas le pipeline
        return {"status": "UNKNOWN", "reason": "Erreur de connexion à Safe Browsing"}