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

    if raw.archive_snapshot_count is not None:
        archive_score = min(raw.archive_snapshot_count / 1000.0, 1.0)
        seo_raw = 0.60 * dr_score + 0.20 * age_score + 0.20 * archive_score
    else:
        # Archive indisponible : redistribution + plafond à 95%
        seo_raw = 0.70 * dr_score + 0.20 * age_score
        seo_raw = min(seo_raw, 0.95)

    seo_normalized = min(max(seo_raw, 0.0), 1.0)
    return round(seo_normalized * 100, 2)