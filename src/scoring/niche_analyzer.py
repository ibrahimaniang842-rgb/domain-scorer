# src/scoring/niche_analyzer.py
import re
import logging

logger = logging.getLogger(__name__)

# Dictionnaire des mots-clés par niche
NICHE_KEYWORDS = {
    "automobile": ["voiture", "auto", "moteur", "garage", "car", "toyota", "ford", "bmw", "renault", "peugeot"],
    "casino": ["casino", "poker", "betting", "gambling", "slot", "jackpot", "blackjack", "roulette"],
    "adult": ["porn", "xxx", "adult", "sex", "escort", "nude", "cam", "live"],
    "pharma": ["viagra", "cialis", "levitra", "pharmacy", "drug", "med", "sildenafil", "tadalafil"],
    "crypto": ["bitcoin", "ethereum", "crypto", "wallet", "blockchain", "coin", "token"],
    "health": ["health", "fitness", "wellness", "medical", "doctor", "clinic", "hospital"],
    "finance": ["finance", "invest", "trade", "forex", "bank", "loan", "credit", "mortgage"],
    "tech": ["tech", "software", "app", "mobile", "cloud", "ai", "data", "digital"],
    "real_estate": ["immobilier", "real estate", "property", "house", "apartment", "rent", "sale"],
    "ecommerce": ["shop", "store", "buy", "sell", "cart", "product", "deal", "discount"],
    "blog": ["blog", "news", "article", "post", "media", "press", "journal"],
    "gaming": ["game", "play", "gaming", "esport", "stream", "twitch", "youtube"]
}

def _detect_niche(text: str) -> str:
    """Détecte la niche dominante dans un texte."""
    if len(text) < 100:
        return "unknown"
    text = text.lower()
    scores = {}
    for niche, keywords in NICHE_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in text)
        if count > 0:
            scores[niche] = count
    if not scores:
        return "unknown"
    return max(scores, key=scores.get)

def analyze_niche_history(snapshots: list) -> dict:
    """
    Analyse l'historique des niches à partir des snapshots.
    Entrée : liste de snapshots de la forme :
    [{"timestamp": "...", "year": "...", "text": "..."}]
    """
    if not snapshots or len(snapshots) < 2:
        return {
            "history": [],
            "shift_detected": False,
            "shift_message": "Pas assez d'historique",
            "confidence": 0
        }

    history = []
    for snap in snapshots:
        text = snap.get("text", "")
        if not text or len(text) < 100:
            continue
        niche = _detect_niche(text)
        year = snap.get("year", "??")
        history.append({
            "timestamp": snap.get("timestamp", ""),
            "year": year,
            "niche": niche if niche != "unknown" else "Non détectée"
        })

    if len(history) < 2:
        return {
            "history": history,
            "shift_detected": False,
            "shift_message": "Historique insuffisant pour analyser la niche",
            "confidence": 0
        }

    # Détection de rupture
    first = history[0]["niche"]
    last = history[-1]["niche"]
    shift_detected = (first != last and first != "Non détectée" and last != "Non détectée")

    shift_message = ""
    confidence = 0
    if shift_detected:
        shift_message = f"⚠️ Changement de niche détecté : {first} → {last}"
        confidence = 80
        toxic = ["casino", "adult", "pharma"]
        if last in toxic:
            confidence = 95
            shift_message += " (niche à risque SEO)"
    else:
        shift_message = "Niches stables ou inconnues"

    return {
        "history": history,
        "shift_detected": shift_detected,
        "shift_message": shift_message,
        "confidence": confidence
    }