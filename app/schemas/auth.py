from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class RegisterTenant(BaseModel):
    company_name: str = Field(min_length=2)
    slug: str = Field(min_length=2, pattern=r"^[a-z0-9-]+$")
    admin_email: EmailStr
    admin_password: str = Field(min_length=8)
    admin_name: str = ""
    base_currency: str = "USD"


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tenant_id: str
    user_id: str


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    is_owner: bool
    roles: list[str]
    permissions: list[str]


class CreateUser(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = ""
    roles: list[str] = ["viewer"]
