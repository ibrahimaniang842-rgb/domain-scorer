# src/scoring/danger.py
from src.core.models import RawData, Danger

HIGH_DR_OVERRIDE = 50.0
LOW_DR_THRESHOLD = 10.0
YOUNG_AGE_DAYS = 90
LOW_ARCHIVE_COUNT = 10

def compute_danger(raw: RawData) -> Danger:
    dr = raw.ahrefs_dr
    age = raw.whois_age_days
    archive_exists = raw.archive_exists
    archive_status = raw.archive_status
    archive_first_date = raw.archive_first_date
    archive_last_date = raw.archive_last_date
    blacklist = raw.blacklist_status

    # --- 1. RÈGLE PRIORITAIRE : BLACKLIST ---
    if blacklist is not None and blacklist != "SAFE" and blacklist != "UNKNOWN":
        return Danger(
            "RED",
            [f"⚠️ DOMAINE BLACKLISTÉ : {raw.blacklist_reason or blacklist}"]
        )

    # --- 2. RÈGLE D'OVERRIDE DR (conditionnel) ---
    # On considère qu'il y a un historique si archive_exists True et au moins une date
    has_history = archive_exists and archive_first_date is not None
    if dr is not None and dr >= HIGH_DR_OVERRIDE:
        if (age is not None and age > 365) or has_history:
            return Danger("GREEN", ["Haute autorité SEO (DR ≥ 50) avec historique de confiance"])
        # Sinon, on continue l'évaluation

    # --- 3. Archive inconnu sur domaine ancien avec autorité (YELLOW) ---
    # Si l'archive est vide (NO_DATA) et que le domaine est ancien (> 10 ans) et a un DR significatif (> 30)
    if (archive_status == "NO_DATA" or archive_status == "TIMEOUT") and age is not None and age > 3650 and dr is not None and dr >= 30:
        return Danger(
            "YELLOW",
            [
                "⚠️ Archive inconnu sur domaine ancien (vérification recommandée)",
                "Le domaine est ancien mais nous ne pouvons pas vérifier son historique."
            ]
        )

    # --- 4. SIGNAUX FAIBLES ---
    low_dr = (dr is None or dr < LOW_DR_THRESHOLD)
    young = (age is not None and age < YOUNG_AGE_DAYS)
    low_archive = (not archive_exists) or (archive_status in ["NO_DATA", "TIMEOUT", "ERROR"])

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