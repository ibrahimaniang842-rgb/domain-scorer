# src/scoring/toxicity.py
from src.core.models import RawData

def compute_toxicity(raw: RawData) -> dict:
    score = 0
    reasons = []
    age = raw.whois_age_days
    dr = raw.ahrefs_dr
    archive_status = raw.archive_status
    archive_count = raw.archive_snapshot_count
    blacklist = raw.blacklist_status

    if age is not None and age < 90:
        score += 25
        reasons.append("Domaine très jeune (< 3 mois)")

    if dr is not None and dr < 10:
        score += 20
        reasons.append("Faible autorité SEO (DR < 10)")

    # Gestion intelligente de l'Archive
    if archive_status == "OK" and archive_count is not None and archive_count < 10:
        score += 5
        reasons.append("Historique Archive très limité")
    elif archive_status == "NO_DATA":
        score += 5
        reasons.append("Domaine sans historique archivé")
    elif archive_status == "TIMEOUT":
        # Aucune pénalité pour timeout, mais on mentionne
        reasons.append("Archive non vérifié (timeout) - ignoré")
    elif archive_status == "ERROR":
        reasons.append("Archive non vérifié (erreur) - ignoré")
    # Si archive_status est None (cas deep_scan=False), on ignore

    if dr is not None and age is not None and dr >= 50 and age < 180:
        score += 30
        reasons.append("DR élevé sur domaine récent - suspect")

    if age is not None and archive_count is not None and age > 3650 and archive_count == 0:
        score += 5
        reasons.append("Domaine ancien sans historique connu")

    if blacklist is not None and blacklist != "SAFE" and blacklist != "UNKNOWN":
        score += 50
        reasons.append(f"Domaine blacklisté (sécurité) : {blacklist}")

    reasons = list(dict.fromkeys(reasons))

    if score >= 60:
        level = "TOXIC"
    elif score >= 30:
        level = "SUSPICIOUS"
    else:
        level = "SAFE"

    return {"score": min(score, 100), "level": level, "reasons": reasons}