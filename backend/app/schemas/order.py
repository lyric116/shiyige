from pydantic import BaseModel


class CreateOrderRequest(BaseModel):
    address_id: int
    idempotency_key: str
    buyer_note: str | None = None


class PayOrderRequest(BaseModel):
    payment_method: str
