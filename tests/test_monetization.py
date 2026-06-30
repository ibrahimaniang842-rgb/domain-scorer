from src.scoring.monetization import compute_monetization_score


def test_monetization_premium_keyword():
    assert compute_monetization_score("crypto-wallet.com") > compute_monetization_score("abcdefgh.com")


def test_monetization_penalizes_hyphens():
    assert compute_monetization_score("my-shop.com") > compute_monetization_score("my-long-shop-name.com")
