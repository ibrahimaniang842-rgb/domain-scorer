# src/scoring/seo.py
from src.core.models import RawData

def compute_seo_score(raw: RawData) -> float:
    if raw.ahrefs_dr is not None:
        dr_raw = raw.ahrefs_dr / 100.0
        dr_score = dr_raw ** 1.2
    else:
        dr_score = 0.0

    if raw.whois_age_days is not None:
        age_score = min(raw.whois_age_days / 3650.0, 1.0)
    else:
        age_score = 0.3

    # Archive n'est plus utilisé dans le score SEO
    seo_raw = 0.75 * dr_score + 0.25 * age_score
    seo_normalized = min(max(seo_raw, 0.0), 1.0)
    return round(seo_normalized * 100, 2)