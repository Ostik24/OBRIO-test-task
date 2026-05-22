from math import ceil
import requests

class AppleReviewsError(Exception):
    """Base error for Apple Reviews API."""

class AppNotFoundError(AppleReviewsError):
    """ID of the app doesn't exist or has no reviews."""


def fetch_reviews(app_id: str, country: str = "us", limit: int = 100) -> list[dict]:
    if not app_id.isdigit():
        raise ValueError("ID of the app must be numeric")
    if len(country) != 2 or not country.isalpha():
        raise ValueError("country must has 2 letters code")
    if limit <= 0:
        raise ValueError("limit must be greater than 0")

    num_pages = ceil(limit / 50) + 1
    reviews = []
    seen = set()

    for page in range(1, num_pages+1):

        url = f"https://itunes.apple.com/{country.lower()}/rss/customerreviews/page={page}/id={app_id}/sortBy=mostRecent/json"

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
            break

        for entry in entries:
            rating_label = entry.get("im:rating", {}).get("label", "")
            if not rating_label or not rating_label.isdigit():
                continue
            rating = int(rating_label)
            if not 1 <= rating <= 5:
                continue

            if (rev_id := entry.get("id", {}).get("label", "")) in seen:
                continue
            seen.add(rev_id)

            reviews.append({
                "author": entry.get("author", {}).get("name", {}).get("label", ""),
                "title": entry.get("title", {}).get("label", ""),
                "content": entry.get("content", {}).get("label", ""),
                "rating": rating,
                "version": entry.get("im:version", {}).get("label", ""),
                "updated": entry.get("updated", {}).get("label", ""),
            })

    return reviews[:limit]


if __name__ == "__main__":
    app_reviews = fetch_reviews("547702041")
    print(app_reviews, len(app_reviews))
