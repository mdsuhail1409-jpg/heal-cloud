"""
User Pydantic Validation Schemas
"""

import re
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("Password must contain at least one letter.")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number.")
        return v


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("Password must contain at least one letter.")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number.")
        return v


class UserRead(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    is_active: bool
    is_platform_admin: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
