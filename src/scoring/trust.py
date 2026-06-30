from dataclasses import dataclass
from typing import List, Optional

from src.core.models import RawData

HIGH_DR_THRESHOLD = 50.0
SUSPICIOUS_DR_THRESHOLD = 30.0
YOUNG_DOMAIN_DAYS = 90
RECENT_DOMAIN_DAYS = 180
MATURE_DOMAIN_DAYS = 365
MIN_ARCHIVE_SPAN_YEARS = 2


@dataclass
class TrustAssessment:
    fraud_risk: bool
    fraud_penalty: float
    has_minimum_history: bool
    history_reasons: List[str]
    trust_reasons: List[str]


def _snapshot_year(value: Optional[str]) -> Optional[int]:
    if not value or len(value) < 4:
        return None
    try:
        return int(value[:4])
    except ValueError:
        return None


def _archive_span_years(raw: RawData) -> Optional[int]:
    first = _snapshot_year(raw.archive_first_date)
    last = _snapshot_year(raw.archive_last_date)
    if first is None or last is None:
        return None
    return max(0, last - first)


def has_minimum_trust_history(raw: RawData) -> tuple[bool, List[str]]:
    reasons: List[str] = []
    age = raw.whois_age_days
    archive_ok = raw.archive_exists is True and raw.archive_status == "OK"

    if age is not None and age >= MATURE_DOMAIN_DAYS:
        reasons.append("Domaine enregistré depuis plus d'un an")
        return True, reasons

    if not archive_ok:
        reasons.append("Historique Archive insuffisant pour valider l'autorité")
        return False, reasons

    span = _archive_span_years(raw)
    first_year = _snapshot_year(raw.archive_first_date)
    if span is not None and span >= MIN_ARCHIVE_SPAN_YEARS:
        reasons.append(f"Archive couvre au moins {MIN_ARCHIVE_SPAN_YEARS} ans")
        return True, reasons

    if first_year is not None and age is not None:
        domain_birth_year = 2026 - (age // 365)
        if first_year <= domain_birth_year + 1:
            reasons.append("Premier snapshot cohérent avec l'âge du domaine")
            return True, reasons

    reasons.append("Historique Archive trop court pour un override GREEN")
    return False, reasons


def compute_trust_assessment(raw: RawData) -> TrustAssessment:
    dr = raw.ahrefs_dr
    age = raw.whois_age_days
    trust_reasons: List[str] = []
    fraud_risk = False
    fraud_penalty = 0.0

    has_history, history_reasons = has_minimum_trust_history(raw)

    if dr is not None and age is not None:
        if dr >= HIGH_DR_THRESHOLD and age < RECENT_DOMAIN_DAYS:
            fraud_risk = True
            fraud_penalty = 0.45
            trust_reasons.append(
                f"Trust Factor: DR élevé ({dr:.0f}) sur domaine récent ({age} jours) — risque PBN/redirect"
            )
        elif dr >= SUSPICIOUS_DR_THRESHOLD and age < YOUNG_DOMAIN_DAYS:
            fraud_risk = True
            fraud_penalty = 0.30
            trust_reasons.append(
                f"Trust Factor: autorité anormale (DR {dr:.0f}) sur domaine très jeune ({age} jours)"
            )

    if raw.niche_shift and raw.niche_shift.get("shift_detected"):
        last_niche = ""
        history = raw.niche_shift.get("history") or []
        if history:
            last_niche = history[-1].get("niche", "")
        if last_niche in {"casino", "adult", "pharma"}:
            fraud_risk = True
            fraud_penalty = max(fraud_penalty, 0.35)
            trust_reasons.append("Changement de niche vers une thématique à risque SEO")

    return TrustAssessment(
        fraud_risk=fraud_risk,
        fraud_penalty=fraud_penalty,
        has_minimum_history=has_history,
        history_reasons=history_reasons,
        trust_reasons=trust_reasons,
    )
