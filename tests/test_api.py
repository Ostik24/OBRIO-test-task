from datetime import datetime
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.api.main import app
from app.models.review import Review
from app.storage import cache


client = TestClient(app)


def _fake_reviews() -> list[Review]:
    return [
        Review(
            id="1", rating=5, title="Great", content="I love this app",
            updated=datetime(2025, 1, 1), sentiment="positive",
            cleaned_content="i love this app",
        ),
        Review(
            id="2", rating=1, title="Bad", content="This app is terrible",
            updated=datetime(2025, 1, 2), sentiment="negative",
            cleaned_content="this app is terrible",
        ),
    ]


def setup_function():
    cache.clear()


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_collect_invalid_app_id():
    r = client.post("/reviews/collect", json={"app_id": "abc"})
    assert r.status_code == 422  # Pydantic pattern validation


def test_collect_missing_app_id():
    r = client.post("/reviews/collect", json={})
    assert r.status_code == 422


def test_metrics_without_collect():
    r = client.get("/reviews/999/metrics")
    assert r.status_code == 404


def test_insights_without_collect():
    r = client.get("/reviews/999/insights")
    assert r.status_code == 404


def test_raw_without_collect():
    r = client.get("/reviews/999/raw")
    assert r.status_code == 404


@patch("app.api.routes.fetch_reviews")
def test_full_flow_with_mock(mock_fetch):
    mock_fetch.return_value = _fake_reviews()
    
    # Collect
    r = client.post("/reviews/collect", json={"app_id": "547702041"})
    assert r.status_code == 200
    body = r.json()
    assert body["fetched"] == 2
    assert body["app_id"] == "547702041"
    assert body["cached"] is True
    
    # Metrics
    r = client.get("/reviews/547702041/metrics")
    assert r.status_code == 200
    metrics = r.json()
    assert metrics["total_reviews"] == 2
    assert metrics["average_rating"] == 3.0
    
    # Raw JSON
    r = client.get("/reviews/547702041/raw")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    assert data[0]["id"] == "1"
    
    # Raw CSV
    r = client.get("/reviews/547702041/raw?format=csv")
    assert r.status_code == 200
    assert "id,author,title" in r.text
    assert "I love this app" in r.text


@patch("app.api.routes.fetch_reviews")
def test_collect_empty_returns_404(mock_fetch):
    mock_fetch.return_value = []
    r = client.post("/reviews/collect", json={"app_id": "547702041"})
    assert r.status_code == 404


@patch("app.api.routes.fetch_reviews")
def test_collect_upstream_error(mock_fetch):
    from app.services.apple_reviews import AppleReviewsError
    mock_fetch.side_effect = AppleReviewsError("network down")
    r = client.post("/reviews/collect", json={"app_id": "547702041"})
    assert r.status_code == 502


@patch("app.api.routes.fetch_reviews")
def test_collect_app_not_found(mock_fetch):
    from app.services.apple_reviews import AppNotFoundError
    mock_fetch.side_effect = AppNotFoundError("not found")
    r = client.post("/reviews/collect", json={"app_id": "547702041"})
    assert r.status_code == 404
