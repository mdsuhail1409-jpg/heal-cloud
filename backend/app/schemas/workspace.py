"""
Workspace Pydantic Validation Schemas
"""

import re
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip().lower()
            if not re.match(r"^[a-z0-9-]+$", v):
                raise ValueError("Slug must contain only lowercase alphanumeric characters and hyphens.")
        return v


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None


class WorkspaceRead(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    slug: str
    description: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
