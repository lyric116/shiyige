from decimal import Decimal

from pydantic import BaseModel, Field


class SemanticSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    limit: int = Field(default=10, ge=1, le=20)
    category_id: int | None = None
    min_price: Decimal | None = None
    max_price: Decimal | None = None
