from src.core.models import RawData
from src.scoring.trust import compute_trust_assessment, has_minimum_trust_history


def _raw(**kwargs) -> RawData:
    defaults = {"domain": "example.com"}
    defaults.update(kwargs)
    return RawData(**defaults)


def test_high_dr_recent_domain_triggers_fraud():
    assessment = compute_trust_assessment(
        _raw(ahrefs_dr=55.0, whois_age_days=60, archive_exists=True, archive_status="OK")
    )
    assert assessment.fraud_risk is True
    assert assessment.fraud_penalty >= 0.40


def test_mature_domain_with_history_passes_trust():
    has_history, _ = has_minimum_trust_history(
        _raw(
            whois_age_days=800,
            archive_exists=True,
            archive_status="OK",
            archive_first_date="20180101120000",
            archive_last_date="20240101120000",
        )
    )
    assert has_history is True


def test_high_dr_without_history_blocked_for_green_override():
    has_history, reasons = has_minimum_trust_history(
        _raw(
            ahrefs_dr=60.0,
            whois_age_days=120,
            archive_exists=False,
            archive_status="NO_DATA",
        )
    )
    assert has_history is False
    assert any("insuffisant" in r.lower() for r in reasons)


def test_archive_span_grants_minimum_history():
    has_history, _ = has_minimum_trust_history(
        _raw(
            whois_age_days=200,
            archive_exists=True,
            archive_status="OK",
            archive_first_date="20190101120000",
            archive_last_date="20240101120000",
        )
    )
    assert has_history is True
