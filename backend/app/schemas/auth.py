"""
Authentication & Authorization Pydantic Schemas
"""

import uuid
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.schemas.user import UserRead


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=2, max_length=255)
    organization_name: Optional[str] = Field(None, min_length=2, max_length=255)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        import re
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("Password must contain at least one letter.")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number.")
        return v


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead


class UserMembershipInfo(BaseModel):
    organization_id: uuid.UUID
    organization_name: str
    organization_slug: str
    role: str


class UserProfileResponse(BaseModel):
    user: UserRead
    memberships: List[UserMembershipInfo]

