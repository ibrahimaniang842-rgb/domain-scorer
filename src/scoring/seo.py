from src.core.models import RawData
from src.scoring.trust import compute_trust_assessment


def compute_seo_score(raw: RawData) -> float:
    trust = compute_trust_assessment(raw)

    if raw.ahrefs_dr is not None and raw.ahrefs_dr <= 0:
        age_bonus = 0.0
        if raw.whois_age_days is not None:
            age_bonus = min(raw.whois_age_days / 3650.0, 1.0) * 0.05
        return round(age_bonus * 100, 2)

    if raw.ahrefs_dr is not None:
        dr_score = (raw.ahrefs_dr / 100.0) ** 1.2
    else:
        dr_score = 0.0

    if raw.whois_age_days is not None:
        age_score = min(raw.whois_age_days / 3650.0, 1.0)
    else:
        age_score = 0.25

    seo_raw = 0.75 * dr_score + 0.25 * age_score
    seo_raw *= max(0.0, 1.0 - trust.fraud_penalty)

    if raw.archive_status == "TIMEOUT":
        seo_raw *= 0.95
    elif raw.archive_status == "ERROR":
        seo_raw *= 0.90

    return round(min(max(seo_raw, 0.0), 1.0) * 100, 2)
