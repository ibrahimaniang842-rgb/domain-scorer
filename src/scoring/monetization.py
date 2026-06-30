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
    "shop", "store", "deal", "coupon", "discount",
}

TLD_BONUS = {
    "com": 1.0,
    "fr": 0.95,
    "io": 0.90,
    "co": 0.85,
    "net": 0.85,
    "org": 0.80,
}


def compute_monetization_score(domain: str) -> float:
    parts = domain.lower().split(".")
    name = parts[0]
    tld = parts[-1] if len(parts) > 1 else ""

    digits = sum(c.isdigit() for c in name)
    hyphens = name.count("-")
    readability = 1.0 - min((digits + hyphens) / max(len(name), 1), 0.5)
    length_score = 1.0 - min(len(name) / 15.0, 1.0)
    keyword_score = 1.0 if any(kw in name for kw in PREMIUM_KEYWORDS) else 0.0
    tld_score = TLD_BONUS.get(tld, 0.70)

    mono_raw = (
        0.40 * readability
        + 0.25 * length_score
        + 0.20 * keyword_score
        + 0.15 * tld_score
    )
    return round(min(max(mono_raw, 0.0), 1.0) * 100, 2)
