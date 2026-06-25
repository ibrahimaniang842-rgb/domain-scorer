# src/scoring/danger.py
from src.core.models import RawData, Danger

HIGH_DR_OVERRIDE = 50.0
LOW_DR_THRESHOLD = 10.0
YOUNG_AGE_DAYS = 90
LOW_ARCHIVE_COUNT = 10

def compute_danger(raw: RawData) -> Danger:
    dr = raw.ahrefs_dr
    age = raw.whois_age_days
    archive = raw.archive_snapshot_count
    
    # --- RÈGLE PRIORITAIRE ABSOLUE : BLACKLIST ---
    if raw.blacklist_status is not None and raw.blacklist_status != "SAFE" and raw.blacklist_status != "UNKNOWN":
        return Danger(
            "RED",
            [f"⚠️ DOMAINE BLACKLISTÉ : {raw.blacklist_reason or raw.blacklist_status}"]
        )

    # --- RÈGLE D'OVERRIDE DR (conditionnel) ---
    if dr is not None and dr >= HIGH_DR_OVERRIDE:
        if (age is not None and age > 365) or (archive is not None and archive > 100):
            return Danger("GREEN", ["Haute autorité SEO (DR ≥ 50) avec historique de confiance"])
        # Sinon, on continue l'évaluation

    # --- SIGNAUX FAIBLES ---
    low_dr = (dr is None or dr < LOW_DR_THRESHOLD)
    young = (age is not None and age < YOUNG_AGE_DAYS)
    low_archive = (archive is None or archive < LOW_ARCHIVE_COUNT)

    weak_signals = sum([low_dr, young, low_archive])

    # ROUGE : 3 signaux faibles
    if weak_signals == 3:
        return Danger(
            "RED",
            [
                "Aucune autorité SEO (DR < 10)",
                "Domaine très récent (< 3 mois)",
                "Aucun historique Archive.org"
            ]
        )

    # JAUNE : 2 signaux faibles
    if weak_signals >= 2:
        reasons = []
        if low_dr:
            reasons.append("Faible autorité SEO (DR < 10)")
        if young:
            reasons.append("Domaine récent (< 3 mois)")
        if low_archive:
            reasons.append("Historique Archive insuffisant ou absent")
        return Danger("YELLOW", reasons)

    # VERT : 0 ou 1 signal faible
    reasons = []
    if low_dr:
        reasons.append("Faible autorité SEO (DR < 10) - reste exploitable")
    if young:
        reasons.append("Domaine récent (< 3 mois) - reste exploitable")
    if low_archive:
        reasons.append("Historique Archive limité - reste exploitable")
    if not reasons:
        reasons.append("Tous les signaux SEO sont sains ou stables")

    return Danger("GREEN", reasons)