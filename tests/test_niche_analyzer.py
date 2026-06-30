import pytest
from datetime import datetime, timedelta, timezone

from src.scoring.niche_analyzer import analyze_niche_history, _filter_snapshots_by_whois


def _blog_text():
    return " " * 50 + "blog news article media press journal " * 20


def _casino_text():
    return " " * 50 + "casino poker betting gambling slot jackpot " * 20


def test_niche_analysis_requires_two_snapshots():
    result = analyze_niche_history([{"timestamp": "20200101", "year": 2020, "text": "x" * 120}])
    assert result["analysis_status"] == "INSUFFICIENT"


def test_niche_shift_detected():
    snapshots = [
        {
            "timestamp": "20150101120000",
            "year": 2015,
            "text": _blog_text(),
        },
        {
            "timestamp": "20240101120000",
            "year": 2024,
            "text": _casino_text(),
        },
    ]
    result = analyze_niche_history(snapshots)
    assert result["shift_detected"] is True
    assert result["analysis_status"] == "OK"
    assert all(entry["year"] != "??" for entry in result["history"])


def test_niche_year_fallback_from_timestamp():
    snapshots = [
        {"timestamp": "20180101120000", "year": 0, "text": "blog news article " * 30},
        {"timestamp": "20220101120000", "year": 0, "text": "blog news article " * 30},
    ]
    result = analyze_niche_history(snapshots)
    assert result["history"][0]["year"] == "2018"


def test_niche_ignores_snapshots_before_whois_creation():
    """openai.com-style bug: archives predating domain registration are dropped."""
    creation = datetime.now(timezone.utc) - timedelta(days=365 * 10)
    pre_creation_year = creation.year - 5

    snapshots = [
        {
            "timestamp": f"{pre_creation_year}0101120000",
            "year": pre_creation_year,
            "text": _casino_text(),
        },
        {
            "timestamp": f"{creation.year + 1}0101120000",
            "year": creation.year + 1,
            "text": _blog_text(),
        },
        {
            "timestamp": "20240101120000",
            "year": 2024,
            "text": _blog_text(),
        },
    ]
    whois_age_days = (datetime.now(timezone.utc) - creation).days
    filtered = _filter_snapshots_by_whois(snapshots, whois_age_days)
    assert len(filtered) == 2
    assert all(int(s["timestamp"][:4]) >= creation.year for s in filtered)

    result = analyze_niche_history(snapshots, whois_age_days=whois_age_days)
    assert result["analysis_status"] == "OK"
    assert all(int(entry["year"]) >= creation.year for entry in result["history"])


def test_niche_without_whois_keeps_all_snapshots():
    snapshots = [
        {"timestamp": "20010101120000", "year": 2001, "text": _blog_text()},
        {"timestamp": "20240101120000", "year": 2024, "text": _blog_text()},
    ]
    result = analyze_niche_history(snapshots, whois_age_days=None)
    assert len(result["history"]) == 2
