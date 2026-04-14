from pydantic import BaseModel, Field


class CreateReviewRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    content: str = Field(..., min_length=1, max_length=2000)
    is_anonymous: bool = False
    image_urls: list[str] = Field(default_factory=list)
