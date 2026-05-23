from datetime import datetime
from app.models.review import Review
from app.services.metrics import (
    total_reviews,
    average_rating,
    rating_distribution,
    sentiment_distribution,
    compute_metrics,
)

def _r(rating: int, sentiment: str = "") -> Review:
    return Review(
        id=f"id-{rating}-{sentiment}",
        rating=rating,
        sentiment=sentiment,
        updated=datetime(2025, 1, 1),
    )

def test_total_reviews():
    assert total_reviews([]) == 0
    assert total_reviews([_r(1), _r(2), _r(3)]) == 3

def test_average_rating_empty():
    assert average_rating([]) == 0.0

def test_average_rating_basic():
    assert average_rating([_r(5), _r(3), _r(1)]) == 3.0
    assert average_rating([_r(5), _r(5), _r(5)]) == 5.0

def test_average_rating_rounding():
    # (5+4+3+1) / 4 = 3.25
    assert average_rating([_r(5), _r(4), _r(3), _r(1)]) == 3.25

def test_rating_distribution_has_all_stars():
    dist = rating_distribution([_r(5), _r(5)])
    assert set(dist.keys()) == {1, 2, 3, 4, 5}
    assert dist[5]["count"] == 2
    assert dist[5]["percent"] == 100.0
    assert dist[1]["count"] == 0
    assert dist[1]["percent"] == 0.0

def test_rating_distribution_mixed():
    dist = rating_distribution([_r(1), _r(1), _r(5), _r(5)])
    assert dist[1]["percent"] == 50.0
    assert dist[5]["percent"] == 50.0

def test_sentiment_distribution_empty():
    dist = sentiment_distribution([])
    assert dist["positive"]["count"] == 0
    assert dist["negative"]["percent"] == 0.0

def test_sentiment_distribution_basic():
    reviews = [_r(1, "negative"), _r(5, "positive"), _r(3, "neutral")]
    dist = sentiment_distribution(reviews)
    assert dist["negative"]["count"] == 1
    assert dist["positive"]["count"] == 1
    assert dist["neutral"]["count"] == 1

def test_compute_metrics_bundle():
    reviews = [_r(5, "positive"), _r(1, "negative")]
    out = compute_metrics(reviews)
    assert out["total_reviews"] == 2
    assert out["average_rating"] == 3.0
    assert "rating_distribution" in out
    assert "sentiment_distribution" in out
