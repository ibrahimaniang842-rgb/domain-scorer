# src/scoring/seo.py
from src.core.models import RawData

def compute_seo_score(raw: RawData) -> float:
    # 1. DR : loi de puissance
    if raw.ahrefs_dr is not None:
        dr_raw = raw.ahrefs_dr / 100.0
        dr_score = dr_raw ** 1.2
    else:
        dr_score = 0.0

    # 2. Age : linéaire, plafonné à 10 ans
    if raw.whois_age_days is not None:
        age_score = min(raw.whois_age_days / 3650.0, 1.0)
    else:
        age_score = 0.3

    # 3. Archive : si présent, bonus ; sinon redistribution
    if raw.archive_snapshot_count is not None:
        archive_score = min(raw.archive_snapshot_count / 1000.0, 1.0)
        # Formule nominale
        seo_raw = 0.60 * dr_score + 0.20 * age_score + 0.20 * archive_score
    else:
        # Archive indisponible : redistribution sur DR (75%) et Age (25%)
        seo_raw = 0.75 * dr_score + 0.25 * age_score

    seo_normalized = min(max(seo_raw, 0.0), 1.0)
    return round(seo_normalized * 100, 2)