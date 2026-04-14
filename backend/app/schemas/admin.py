from decimal import Decimal

from pydantic import BaseModel, Field


class AdminProductSkuRequest(BaseModel):
    sku_code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    price: Decimal = Field(gt=0)
    member_price: Decimal | None = Field(default=None, gt=0)
    inventory: int = Field(ge=0)
    is_active: bool = True


class AdminProductUpsertRequest(BaseModel):
    category_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=200)
    subtitle: str | None = Field(default=None, max_length=255)
    cover_url: str | None = Field(default=None, max_length=255)
    description: str | None = None
    culture_summary: str | None = None
    dynasty_style: str | None = Field(default=None, max_length=100)
    craft_type: str | None = Field(default=None, max_length=100)
    festival_tag: str | None = Field(default=None, max_length=100)
    scene_tag: str | None = Field(default=None, max_length=100)
    status: int = Field(default=1, ge=0)
    tags: list[str] = Field(default_factory=list)
    media_urls: list[str] = Field(default_factory=list)
    default_sku: AdminProductSkuRequest


class AdminReindexRequest(BaseModel):
    force: bool = True
    product_ids: list[int] | None = None
