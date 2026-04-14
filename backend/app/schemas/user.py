from datetime import date

from pydantic import BaseModel, EmailStr, Field


class UpdateUserProfileRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=4, max_length=100)
    display_name: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
    birthday: date | None = None
    bio: str | None = None
    avatar_url: str | None = Field(default=None, max_length=255)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
