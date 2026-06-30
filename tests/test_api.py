from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_invalid_domain_returns_400():
    response = client.get("/score", params={"domain": "not-a-domain"})
    assert response.status_code == 400


def test_batch_validation_empty_list():
    response = client.post("/batch-score", json={"domains": []})
    assert response.status_code == 422


def test_batch_validation_too_many_domains():
    response = client.post("/batch-score", json={"domains": [f"d{i}.com" for i in range(51)]})
    assert response.status_code == 422


def test_score_endpoint_never_500_on_pipeline_error(monkeypatch):
    async def boom(_domain, use_archive=True):
        raise RuntimeError("simulated outage")

    monkeypatch.setattr("src.main.score_domain", boom)
    response = client.get("/score", params={"domain": "example.com"})
    assert response.status_code == 503
    body = response.json()
    assert body["error"] == "score_failed"


def test_batch_invalid_domain_item():
    response = client.post("/batch-score", json={"domains": ["bad", "example.com"]})
    assert response.status_code == 200
    results = response.json()["results"]
    assert results[0]["danger_level"] == "ERROR"
    assert results[0]["danger_reasons"] == ["Domaine invalide"]
