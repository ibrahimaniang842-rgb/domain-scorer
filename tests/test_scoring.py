from src.core.models import RawData
from src.scoring.danger import compute_danger
from src.scoring.seo import compute_seo_score
from src.scoring.toxicity import compute_toxicity


def _raw(**kwargs) -> RawData:
    defaults = {"domain": "example.com"}
    defaults.update(kwargs)
    return RawData(**defaults)


def test_seo_score_zero_dr():
    score = compute_seo_score(_raw(ahrefs_dr=0.0, whois_age_days=365))
    assert score <= 1.0

    score_no_age = compute_seo_score(_raw(ahrefs_dr=0.0, whois_age_days=None))
    assert score_no_age == 0.0


def test_seo_score_penalized_by_fraud():
    clean = compute_seo_score(_raw(ahrefs_dr=60.0, whois_age_days=4000))
    fraud = compute_seo_score(_raw(ahrefs_dr=60.0, whois_age_days=30))
    assert fraud < clean


def test_danger_red_on_pbn_pattern():
    danger = compute_danger(_raw(ahrefs_dr=55.0, whois_age_days=45, archive_status="NO_DATA"))
    assert danger.level == "RED"


def test_danger_green_high_dr_with_history():
    danger = compute_danger(
        _raw(
            ahrefs_dr=55.0,
            whois_age_days=800,
            archive_exists=True,
            archive_status="OK",
            archive_first_date="20180101120000",
            archive_last_date="20240101120000",
        )
    )
    assert danger.level == "GREEN"


def test_danger_yellow_high_dr_without_history():
    danger = compute_danger(
        _raw(
            ahrefs_dr=55.0,
            whois_age_days=200,
            archive_exists=False,
            archive_status="NO_DATA",
        )
    )
    assert danger.level == "YELLOW"


def test_toxicity_aligned_with_fraud():
    toxicity = compute_toxicity(_raw(ahrefs_dr=60.0, whois_age_days=30))
    assert toxicity["level"] in {"SUSPICIOUS", "TOXIC"}
    assert toxicity["score"] >= 30


def test_toxicity_archive_timeout_adds_caution():
    toxicity = compute_toxicity(_raw(archive_status="TIMEOUT", archive_exists=False))
    assert any("timeout" in r.lower() for r in toxicity["reasons"])
