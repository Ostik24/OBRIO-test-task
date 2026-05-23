from fastapi import FastAPI
from dotenv import load_dotenv

from app.api.routes import router as reviews_router

load_dotenv()

app = FastAPI(
    title="Apple Store Review Analysis API",
    description="Fetch reviews from Apple Store, compute metrics, and extract NLP insights.",
    version="1.0.0"
)

app.include_router(reviews_router)

@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
