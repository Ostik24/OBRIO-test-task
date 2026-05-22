from datetime import datetime
from pydantic import BaseModel, Field

class Review(BaseModel):
    id: str
    author: str = ""
    title: str = ""
    content: str = ""
    rating: int = Field(ge=1, le=5)
    version: str = ""
    updated: datetime
    cleaned_content: str = ""
    sentiment: str = ""
