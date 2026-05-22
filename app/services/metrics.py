from app.models.review import Review

def total_reviews(reviews: list[Review]) -> int:
    return len(reviews)

def average_rating(reviews: list[Review]) -> float:
    if not reviews:
        return 0.0
    return round(sum(review.rating for review in reviews) / total_reviews(reviews), 2)

def rating_distribution(reviews: list[Review]) -> dict:
    counts = {i: sum(1 for r in reviews if r.rating == i) for i in range(1, 6)}
    total = total_reviews(reviews)
    return {j: {
        "count": counts[j],
        "percent": round(counts[j] / total * 100, 1) if total else 0.0,
    } for j in range(1, 6)}

def sentiment_distribution(reviews: list[Review]) -> dict:
    """Counts + percentages of positive/negative/neutral."""
    counts = {s: sum(1 for r in reviews if r.sentiment == s) for s in ["positive", "negative", "neutral"]}
    total = total_reviews(reviews)
    return {s: {
        "count": counts[s],
        "percent": round(counts[s] / total * 100, 1) if total else 0.0,
    } for s in ["positive", "negative", "neutral"]}

def compute_metrics(reviews: list[Review]) -> dict:
    return {
        "total_reviews": total_reviews(reviews),
        "average_rating": average_rating(reviews),
        "rating_distribution": rating_distribution(reviews),
        "sentiment_distribution": sentiment_distribution(reviews),
    }

if __name__ == "__main__":
    from app.services.apple_reviews import fetch_reviews
    from app.services.sentiment import annotate
    reviews_test = fetch_reviews("547702041", limit=100)
    annotate(reviews_test)
    from pprint import pprint
    pprint(compute_metrics(reviews_test))
