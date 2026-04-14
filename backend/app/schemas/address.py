from pydantic import BaseModel, Field


class UserAddressRequest(BaseModel):
    recipient_name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=1, max_length=20)
    region: str = Field(min_length=1, max_length=100)
    detail_address: str = Field(min_length=1, max_length=255)
    postal_code: str | None = Field(default=None, max_length=20)
    is_default: bool = False
