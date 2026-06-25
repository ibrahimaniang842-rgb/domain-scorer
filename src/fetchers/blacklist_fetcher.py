# src/fetchers/blacklist_fetcher.py
import aiohttp
import json
from typing import Optional

# Ta clé API Google Safe Browsing
GOOGLE_SAFE_BROWSING_API_KEY = "AIzaSyB1-RUCkQd10_TdNc3-uF2P6ozR4f9Ktpk"

async def get_blacklist_status(domain: str, session: aiohttp.ClientSession) -> dict:
    """
    Vérifie si un domaine est blacklisté par Google Safe Browsing.
    Retourne : {"status": "SAFE"} ou {"status": "MALWARE", "reason": "..."}
    """
    # Vérification : si la clé est vide ou égale au placeholder, on ne fait pas l'appel
    if GOOGLE_SAFE_BROWSING_API_KEY == "" or GOOGLE_SAFE_BROWSING_API_KEY == "YOUR_API_KEY_HERE":
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
        # Timeout augmenté à 10 secondes pour plus de tolérance
        async with session.post(url, json=payload, timeout=10.0) as resp:
            # Log du statut HTTP (visible dans les logs Render)
            print(f"[BLACKLIST] {domain} -> status {resp.status}")
            
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
            
    except TimeoutError:
        print(f"[BLACKLIST] {domain} -> TIMEOUT")
        return {"status": "UNKNOWN", "reason": "Timeout de la requête Safe Browsing"}
    except aiohttp.ClientError as e:
        print(f"[BLACKLIST] {domain} -> ERREUR CLIENT: {e}")
        return {"status": "UNKNOWN", "reason": "Erreur de connexion à Safe Browsing"}
    except Exception as e:
        print(f"[BLACKLIST] {domain} -> ERREUR INATTENDUE: {e}")
        return {"status": "UNKNOWN", "reason": f"Erreur inattendue: {str(e)}"}