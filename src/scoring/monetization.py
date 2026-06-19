# src/scoring/monetization.py
import re

PREMIUM_KEYWORDS = {
    "crypto", "blockchain", "bitcoin", "ethereum", "defi",
    "health", "fitness", "wellness", "medical",
    "finance", "invest", "trade", "forex", "bank",
    "ai", "artificial", "intelligence", "ml",
    "insurance", "claims", "coverage",
    "law", "legal", "attorney", "lawyer",
    "travel", "vacation", "holiday",
    "hosting", "cloud", "server", "vpn",
    "casino", "poker", "betting", "sportsbook",
    "shop", "store", "deal", "coupon", "discount"
}

def compute_monetization_score(domain: str) -> float:
    # 1. Readability (pénalise chiffres et tirets)
    name = domain.split('.')[0]
    digits = sum(c.isdigit() for c in name)
    hyphens = name.count('-')
    readability = 1.0 - min((digits + hyphens) / max(len(name), 1), 0.5)

    # 2. Length (court = meilleur)
    length_score = 1.0 - min(len(name) / 15.0, 1.0)

    # 3. Keyword match
    keyword_score = 1.0 if any(kw in name.lower() for kw in PREMIUM_KEYWORDS) else 0.0

    # 4. Poids
    mono_raw = 0.50 * readability + 0.30 * length_score + 0.20 * keyword_score
    mono_normalized = min(max(mono_raw, 0.0), 1.0)
    return round(mono_normalized * 100, 2)