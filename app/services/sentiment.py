from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from app.models.review import Review

_analyzer = SentimentIntensityAnalyzer()

def classify(text: str) -> str:
    if not text:
        return "neutral"
    score = _analyzer.polarity_scores(text)["compound"]
    if score >= 0.05:
        return "positive"
    if score <= -0.05:
        return "negative"
    return "neutral"

def annotate(reviews: list[Review]) -> list[Review]:
    for r in reviews:
        text = f"{r.title}. {r.content}"
        sentiment = classify(text)
        if r.rating == 1 and sentiment == "positive":
            sentiment = "negative"
        elif r.rating == 5 and sentiment == "negative":
            sentiment = "positive"
        r.sentiment = sentiment
    return reviews


if __name__ == "__main__":
    from app.services.apple_reviews import fetch_reviews
    reviews = fetch_reviews("547702041", limit=10)
    annotate(reviews)
    for r in reviews:
        print(r.rating, r.sentiment, r.title)
