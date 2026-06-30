from src.core.models import RawData, Danger
from src.scoring.trust import (
    HIGH_DR_THRESHOLD,
    YOUNG_DOMAIN_DAYS,
    compute_trust_assessment,
    has_minimum_trust_history,
)

LOW_DR_THRESHOLD = 10.0


def compute_danger(raw: RawData) -> Danger:
    dr = raw.ahrefs_dr
    age = raw.whois_age_days
    archive_status = raw.archive_status
    blacklist = raw.blacklist_status
    trust = compute_trust_assessment(raw)

    if blacklist not in (None, "SAFE", "UNKNOWN"):
        return Danger(
            "RED",
            [f"Domaine blacklisté : {raw.blacklist_reason or blacklist}"],
        )

    if trust.fraud_risk:
        return Danger(
            "RED",
            trust.trust_reasons
            + ["Autorité SEO incohérente avec l'âge du domaine — risque de spam/redirect"],
        )

    has_history, history_reasons = has_minimum_trust_history(raw)
    if dr is not None and dr >= HIGH_DR_THRESHOLD and has_history:
        return Danger(
            "GREEN",
            [f"Haute autorité SEO (DR ≥ {int(HIGH_DR_THRESHOLD)})"] + history_reasons,
        )

    if dr is not None and dr >= HIGH_DR_THRESHOLD and not has_history:
        return Danger(
            "YELLOW",
            [
                f"DR élevé ({dr:.0f}) sans historique Archive/âge suffisant",
                "Vérification manuelle recommandée avant achat",
            ],
        )

    if archive_status in {"TIMEOUT", "ERROR"} and age is not None and age > 3650 and dr is not None and dr >= 30:
        return Danger(
            "YELLOW",
            [
                "Archive.org indisponible sur un domaine ancien à forte autorité",
                "Impossible de confirmer l'historique — vérification manuelle requise",
            ],
        )

    low_dr = dr is None or dr < LOW_DR_THRESHOLD
    young = age is not None and age < YOUNG_DOMAIN_DAYS
    low_archive = (
        raw.archive_exists is not True
        or archive_status in {"NO_DATA", "TIMEOUT", "ERROR"}
    )

    weak_signals = sum([low_dr, young, low_archive])

    if weak_signals >= 3:
        return Danger(
            "RED",
            [
                "Aucune autorité SEO significative (DR < 10)",
                "Domaine très récent (< 3 mois)",
                "Historique Archive absent ou non vérifiable",
            ],
        )

    if weak_signals >= 2:
        reasons = []
        if low_dr:
            reasons.append("Faible autorité SEO (DR < 10)")
        if young:
            reasons.append("Domaine récent (< 3 mois)")
        if low_archive:
            if archive_status == "TIMEOUT":
                reasons.append("Archive.org timeout — historique non confirmé")
            else:
                reasons.append("Historique Archive insuffisant ou absent")
        return Danger("YELLOW", reasons)

    reasons = []
    if low_dr:
        reasons.append("Faible autorité SEO (DR < 10) — reste exploitable")
    if young:
        reasons.append("Domaine récent (< 3 mois) — reste exploitable")
    if low_archive:
        if archive_status == "TIMEOUT":
            reasons.append("Archive.org timeout — score basé sur DR/âge uniquement")
        else:
            reasons.append("Historique Archive limité — reste exploitable")
    if not reasons:
        reasons.append("Signaux SEO cohérents et stables")

    return Danger("GREEN", reasons)
