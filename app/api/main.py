import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv
from fastapi.responses import JSONResponse

from app.api.routes import router as reviews_router

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[startup] Warming up embeddings model...")
    from app.services.embeddings import _model
    print("[startup] Ready.")

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("[startup] WARNING: ANTHROPIC_API_KEY not set — recommendations will use templated fallback")

    yield

app = FastAPI(
    title="Apple Store Review Analysis API",
    description="Fetch reviews from Apple Store, compute metrics, and extract NLP insights.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(reviews_router)

@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
