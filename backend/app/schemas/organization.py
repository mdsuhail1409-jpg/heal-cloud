"""
Organization Pydantic Validation Schemas
"""

import re
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: Optional[str] = Field(None, min_length=2, max_length=100)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip().lower()
            if not re.match(r"^[a-z0-9-]+$", v):
                raise ValueError("Slug must contain only lowercase alphanumeric characters and hyphens.")
        return v


class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    slug: Optional[str] = Field(None, min_length=2, max_length=100)
    is_active: Optional[bool] = None

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip().lower()
            if not re.match(r"^[a-z0-9-]+$", v):
                raise ValueError("Slug must contain only lowercase alphanumeric characters and hyphens.")
        return v


class OrganizationRead(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    is_active: bool
    created_at: datetime
    user_role: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
