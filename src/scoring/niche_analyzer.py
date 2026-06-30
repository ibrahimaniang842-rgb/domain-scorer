import re
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)

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
    "gaming": ["game", "play", "gaming", "esport", "stream", "twitch", "youtube"],
}


def _detect_niche(text: str) -> str:
    if len(text) < 100:
        return "unknown"
    text_lower = text.lower()
    scores = {}
    for niche, keywords in NICHE_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in text_lower)
        if count > 0:
            scores[niche] = count
    if not scores:
        return "unknown"
    return max(scores, key=scores.get)


def _format_year(snap: dict) -> str:
    year = snap.get("year")
    if isinstance(year, int) and year > 1990:
        return str(year)
    timestamp = snap.get("timestamp", "")
    if len(timestamp) >= 4 and timestamp[:4].isdigit():
        return timestamp[:4]
    return "inconnue"


def _domain_creation_date(whois_age_days: Optional[int]) -> Optional[datetime]:
    if whois_age_days is None or whois_age_days < 0:
        return None
    return datetime.now(timezone.utc) - timedelta(days=whois_age_days)


def _parse_snapshot_date(snap: dict) -> Optional[datetime]:
    timestamp = snap.get("timestamp", "")
    if len(timestamp) >= 8 and timestamp[:8].isdigit():
        try:
            return datetime(
                int(timestamp[:4]),
                int(timestamp[4:6]),
                int(timestamp[6:8]),
                tzinfo=timezone.utc,
            )
        except ValueError:
            pass

    year = snap.get("year")
    if isinstance(year, int) and year > 1990:
        return datetime(year, 1, 1, tzinfo=timezone.utc)

    if len(timestamp) >= 4 and timestamp[:4].isdigit():
        return datetime(int(timestamp[:4]), 1, 1, tzinfo=timezone.utc)

    return None


def _is_snapshot_chronologically_valid(snap: dict, creation_date: Optional[datetime]) -> bool:
    if creation_date is None:
        return True

    snap_date = _parse_snapshot_date(snap)
    if snap_date is None:
        return False

    if snap_date.date() < creation_date.date():
        return False

    year = snap.get("year")
    if isinstance(year, int) and year > 1990 and year < creation_date.year:
        return False

    return True


def _filter_snapshots_by_whois(snapshots: list, whois_age_days: Optional[int]) -> list:
    creation_date = _domain_creation_date(whois_age_days)
    if creation_date is None:
        return snapshots

    valid = [snap for snap in snapshots if _is_snapshot_chronologically_valid(snap, creation_date)]
    dropped = len(snapshots) - len(valid)
    if dropped:
        logger.info(
            "Ignored %d snapshot(s) predating WHOIS creation (%s)",
            dropped,
            creation_date.date().isoformat(),
        )
    return valid


def analyze_niche_history(snapshots: list, whois_age_days: Optional[int] = None) -> dict:
    snapshots = _filter_snapshots_by_whois(snapshots, whois_age_days)

    if not snapshots or len(snapshots) < 2:
        return {
            "history": [],
            "shift_detected": False,
            "shift_message": "Historique insuffisant pour analyser la niche",
            "confidence": 0,
            "analysis_status": "INSUFFICIENT",
        }

    history = []
    for snap in snapshots:
        text = snap.get("text", "")
        if not text or len(text) < 100:
            continue
        niche = _detect_niche(text)
        history.append({
            "timestamp": snap.get("timestamp", ""),
            "year": _format_year(snap),
            "niche": niche if niche != "unknown" else "Non détectée",
        })

    if len(history) < 2:
        return {
            "history": history,
            "shift_detected": False,
            "shift_message": "Contenu insuffisant pour une analyse fiable de niche",
            "confidence": 0,
            "analysis_status": "INSUFFICIENT",
        }

    first = history[0]["niche"]
    last = history[-1]["niche"]
    known_first = first != "Non détectée"
    known_last = last != "Non détectée"
    shift_detected = known_first and known_last and first != last

    if shift_detected:
        shift_message = f"Changement de niche détecté : {first} → {last}"
        confidence = 80
        if last in {"casino", "adult", "pharma"}:
            confidence = 95
            shift_message += " (niche à risque SEO)"
    else:
        shift_message = "Niches stables ou non identifiables"
        confidence = 40 if known_first else 20

    return {
        "history": history,
        "shift_detected": shift_detected,
        "shift_message": shift_message,
        "confidence": confidence,
        "analysis_status": "OK",
    }
