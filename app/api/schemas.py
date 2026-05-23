from pydantic import BaseModel, Field

class CollectRequest(BaseModel):
    app_id: str = Field(..., pattern=r"^\d+$", description="Numeric Apple app ID, e.g. 547702041")
    country: str = Field("us", min_length=2, max_length=2)
    limit: int = Field(100, ge=1, le=500)

class CollectResponse(BaseModel):
    app_id: str
    country: str
    fetched: int
    cached: bool = False

class ErrorResponse(BaseModel):
    detail: str
