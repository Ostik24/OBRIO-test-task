from pydantic import ValidationError
from app.models.review import Review
from app.services.text_cleaning import clean_review_text
import requests

MAX_PAGES = 10
SORT_KEYS = ["mostHelpful", "mostRecent"]

class AppleReviewsError(Exception):
    """Base error for Apple Reviews API."""

class AppNotFoundError(AppleReviewsError):
    """ID of the app doesn't exist or has no reviews."""


def fetch_reviews(app_id: str, country: str = "us", limit: int = 100) -> list[Review]:
    if not app_id.isdigit():
        raise ValueError("ID of the app must be numeric")
    if len(country) != 2 or not country.isalpha():
        raise ValueError("country must have a 2-letter code")
    if limit <= 0:
        raise ValueError("limit must be greater than 0")

    reviews: list[Review] = []
    seen: set[str] = set()

    for sort_key in SORT_KEYS:
        if len(reviews) >= limit:
            break

        for page in range(1, MAX_PAGES + 1):
            if len(reviews) >= limit:
                break

            url = f"https://itunes.apple.com/{country.lower()}/rss/customerreviews/page={page}/id={app_id}/sortBy={sort_key}/json"

            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()
            except requests.HTTPError as e:
                if e.response.status_code == 404:
                    raise AppNotFoundError(f"app_id {app_id} not found") from e
                raise AppleReviewsError(f"Apple API error: {e}") from e
            except requests.RequestException as e:
                raise AppleReviewsError(f"network error: {e}") from e

            entries = data["feed"].get("entry", [])
            if isinstance(entries, dict):
                entries = [entries]

            if not entries:
                continue

            for entry in entries:
                if len(reviews) >= limit:
                    break
                rating_label = entry.get("im:rating", {}).get("label", "")
                if not rating_label or not rating_label.isdigit():
                    continue
                rating = int(rating_label)
                if not 1 <= rating <= 5:
                    continue

                if (rev_id := entry.get("id", {}).get("label", "")) in seen:
                    continue
                seen.add(rev_id)

                try:
                    reviews.append(Review(
                        id=rev_id,
                        author=entry.get("author", {}).get("name", {}).get("label", ""),
                        title=entry.get("title", {}).get("label", ""),
                        content=(raw_content := entry.get("content", {}).get("label", "")),
                        rating=rating,
                        version=entry.get("im:version", {}).get("label", ""),
                        updated=entry.get("updated", {}).get("label", ""),
                        cleaned_content=clean_review_text(raw_content),
                    ))
                except ValidationError:
                    continue

    return reviews[:limit]


if __name__ == "__main__":
    app_reviews = fetch_reviews("547702041", limit=100)
    for r in app_reviews[:10]:
        print(r.rating, r.title)
        print("  raw:    ", r.content[:80])
        print("  cleaned:", r.cleaned_content[:80])
