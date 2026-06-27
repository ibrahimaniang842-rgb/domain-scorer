# src/scoring/niche_analyzer.py
import re
from bs4 import BeautifulSoup

# Mots-clés par niche (extensibles)
NICHE_KEYWORDS = {
    "automobile": ["voiture", "auto", "moteur", "garage", "car", "toyota", "ford", "bmw"],
    "casino": ["casino", "poker", "betting", "gambling", "slot", "jackpot", "blackjack"],
    "adult": ["porn", "xxx", "adult", "sex", "escort", "nude"],
    "pharma": ["viagra", "cialis", "levitra", "pharmacy", "drug", "med", "sildenafil"],
    "crypto": ["bitcoin", "ethereum", "crypto", "wallet", "blockchain", "coin"],
    "health": ["health", "fitness", "wellness", "medical", "doctor", "clinic"],
    "finance": ["finance", "invest", "trade", "forex", "bank", "loan", "credit"],
    "tech": ["tech", "software", "app", "mobile", "cloud", "ai", "data"],
    "real_estate": ["immobilier", "real estate", "property", "house", "apartment", "rent"],
    "ecommerce": ["shop", "store", "buy", "sell", "cart", "product", "deal"],
    "blog": ["blog", "news", "article", "post", "media", "press"],
    "gaming": ["game", "play", "gaming", "esport", "stream"]
}

def _extract_text(html: str) -> str:
    try:
        soup = BeautifulSoup(html, 'html.parser')
        # Supprimer script, style, meta
        for tag in soup(["script", "style", "meta", "noscript"]):
            tag.decompose()
        return soup.get_text(separator=' ', strip=True).lower()
    except:
        return ""

def _detect_niche(text: str) -> str:
    """Retourne la niche dominante ou 'unknown'."""
    scores = {}
    for niche, keywords in NICHE_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in text)
        if count > 0:
            scores[niche] = count
    if not scores:
        return "unknown"
    # Retourner la niche avec le plus d'occurrences
    return max(scores, key=scores.get)

def analyze_niche_history(snapshots: list) -> dict:
    """
    Entrée : liste de snapshots (timestamp, html)
    Sortie : {
        "history": [{"timestamp": "...", "niche": "..."}],
        "shift_detected": bool,
        "shift_message": str,
        "confidence": int (0-100)
    }
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
        text = _extract_text(snap.get("html", ""))
        niche = _detect_niche(text)
        # Formatage de la date pour l'affichage
        ts = snap.get("timestamp", "")
        year = ts[:4] if len(ts) >= 4 else "??"
        history.append({
            "timestamp": ts,
            "year": year,
            "niche": niche if niche != "unknown" else "Non détectée"
        })

    # Détection de rupture : comparer la première et la dernière niche
    first = history[0]["niche"]
    last = history[-1]["niche"]
    shift_detected = (first != last and first != "Non détectée" and last != "Non détectée")

    shift_message = ""
    confidence = 0
    if shift_detected:
        shift_message = f"⚠️ Changement de niche détecté : {first} → {last}"
        confidence = 80
        # Bonus si la niche est toxique
        toxic = ["casino", "adult", "pharma"]
        if last in toxic:
            confidence = 95
            shift_message += " (niche à risque SEO)"
    else:
        shift_message = f"Niches stables ou inconnues"

    return {
        "history": history,
        "shift_detected": shift_detected,
        "shift_message": shift_message,
        "confidence": confidence
    }