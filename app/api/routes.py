from io import StringIO
import csv
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.api.schemas import CollectRequest, CollectResponse
from app.services.apple_reviews import fetch_reviews, AppNotFoundError, AppleReviewsError
from app.services.sentiment import annotate
from app.services.metrics import compute_metrics
from app.services.insights import compute_insights
from app.storage import cache

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post("/collect", response_model=CollectResponse)
def collect_reviews(req: CollectRequest):
    try:
        reviews = fetch_reviews(req.app_id, country=req.country, limit=req.limit)
    except AppNotFoundError as e:
        raise HTTPException(404, str(e))
    except AppleReviewsError as e:
        raise HTTPException(502, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))

    if not reviews:
        raise HTTPException(404, f"no reviews found for app_id {req.app_id}")

    annotate(reviews)
    cache.save(req.app_id, reviews)

    return CollectResponse(
        app_id=req.app_id,
        country=req.country,
        fetched=len(reviews),
        cached=True,
    )


@router.get("/{app_id}/metrics")
def get_metrics(app_id: str):
    reviews = cache.get(app_id)
    if reviews is None:
        raise HTTPException(404, f"no cached reviews for app_id {app_id}. Call POST /reviews/collect first.")
    return compute_metrics(reviews)


@router.get("/{app_id}/insights")
def get_insights(app_id: str):
    reviews = cache.get(app_id)
    if reviews is None:
        raise HTTPException(404, f"no cached reviews for app_id {app_id}. Call POST /reviews/collect first.")
    return compute_insights(reviews)


@router.get("/{app_id}/raw")
def get_raw(
    app_id: str,
    format: str = Query("json", pattern="^(json|csv)$"),
):
    reviews = cache.get(app_id)
    if reviews is None:
        raise HTTPException(404, f"no cached reviews for app_id {app_id}. Call POST /reviews/collect first.")

    if format == "json":
        return [r.model_dump(mode="json") for r in reviews]

    buffer = StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=["id", "author", "title", "content", "rating", "version", "updated", "sentiment"],
    )
    writer.writeheader()
    for r in reviews:
        row = r.model_dump(mode="json")
        row.pop("cleaned_content", None)
        writer.writerow(row)
    buffer.seek(0)

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="reviews_{app_id}.csv"'},
    )
