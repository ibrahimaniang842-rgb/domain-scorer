import pytest

from src.scoring.niche_analyzer import analyze_niche_history


def test_niche_analysis_requires_two_snapshots():
    result = analyze_niche_history([{"timestamp": "20200101", "year": 2020, "text": "x" * 120}])
    assert result["analysis_status"] == "INSUFFICIENT"


def test_niche_shift_detected():
    snapshots = [
        {
            "timestamp": "20150101120000",
            "year": 2015,
            "text": " " * 50 + "blog news article media press journal " * 20,
        },
        {
            "timestamp": "20240101120000",
            "year": 2024,
            "text": " " * 50 + "casino poker betting gambling slot jackpot " * 20,
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
