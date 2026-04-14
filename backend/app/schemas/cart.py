from pydantic import BaseModel


class AddCartItemRequest(BaseModel):
    product_id: int
    sku_id: int
    quantity: int


class UpdateCartItemRequest(BaseModel):
    quantity: int
