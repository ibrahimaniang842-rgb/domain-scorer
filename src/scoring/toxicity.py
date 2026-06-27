# src/scoring/toxicity.py
from src.core.models import RawData

def compute_toxicity(raw: RawData) -> dict:
    score = 0
    reasons = []
    age = raw.whois_age_days
    dr = raw.ahrefs_dr
    archive_exists = raw.archive_exists
    archive_first_date = raw.archive_first_date
    archive_status = raw.archive_status
    blacklist = raw.blacklist_status

    if age is not None and age < 90:
        score += 25
        reasons.append("Domaine très jeune (< 3 mois)")

    if dr is not None and dr < 10:
        score += 20
        reasons.append("Faible autorité SEO (DR < 10)")

    # --- Nouvelle logique Archive basée sur l'existence et les dates ---
    if archive_exists and archive_first_date:
        # Le domaine a une histoire
        if age is not None and age > 3650:
            try:
                first_year = int(archive_first_date[:4])
                # Si le premier snapshot est bien plus tardif que l'âge du domaine, c'est suspect
                if first_year > (age / 365) + 2:
                    score += 10
                    reasons.append("Premier snapshot tardif (domaine ancien, archive récente)")
            except:
                pass
    else:
        # Pas d'archive ou timeout → pas de pénalité, juste un warning
        if archive_status == "TIMEOUT":
            reasons.append("Archive non vérifié (timeout) - ignoré")
        elif archive_status == "NO_DATA":
            reasons.append("Domaine sans historique archivé")

    if dr is not None and age is not None and dr >= 50 and age < 180:
        score += 30
        reasons.append("DR élevé sur domaine récent - suspect")

    if age is not None and age > 3650 and archive_exists is False and archive_status == "NO_DATA":
        score += 5
        reasons.append("Domaine ancien sans aucune archive")

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