from src.core.models import RawData
from src.scoring.trust import compute_trust_assessment


def compute_toxicity(raw: RawData) -> dict:
    score = 0
    reasons = []
    age = raw.whois_age_days
    dr = raw.ahrefs_dr
    archive_status = raw.archive_status
    blacklist = raw.blacklist_status
    trust = compute_trust_assessment(raw)

    if age is not None and age < 90:
        score += 25
        reasons.append("Domaine très jeune (< 3 mois)")

    if dr is not None and dr < 10:
        score += 20
        reasons.append("Faible autorité SEO (DR < 10)")

    if trust.fraud_risk:
        score += int(30 + trust.fraud_penalty * 40)
        reasons.extend(trust.trust_reasons)

    if raw.archive_exists and raw.archive_first_date and age is not None and age > 3650:
        try:
            first_year = int(raw.archive_first_date[:4])
            domain_birth_year = 2026 - (age // 365)
            if first_year > domain_birth_year + 2:
                score += 15
                reasons.append("Premier snapshot Archive tardif par rapport à l'âge WHOIS")
        except ValueError:
            pass

    if archive_status == "TIMEOUT":
        score += 5
        reasons.append("Archive.org timeout — confiance réduite")
    elif archive_status == "NO_DATA" and raw.archive_exists is False:
        if age is not None and age > 3650:
            score += 10
            reasons.append("Domaine ancien sans aucune trace Archive.org")
        else:
            reasons.append("Aucun historique archivé disponible")

    if raw.niche_shift and raw.niche_shift.get("shift_detected"):
        score += 20
        reasons.append(raw.niche_shift.get("shift_message", "Changement de niche détecté"))

    if blacklist not in (None, "SAFE", "UNKNOWN"):
        score += 50
        reasons.append(f"Domaine blacklisté (sécurité) : {blacklist}")

    reasons = list(dict.fromkeys(reasons))
    score = min(score, 100)

    if score >= 60:
        level = "TOXIC"
    elif score >= 30:
        level = "SUSPICIOUS"
    else:
        level = "SAFE"

    return {"score": score, "level": level, "reasons": reasons}
