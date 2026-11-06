"""
Membership Pydantic Validation Schemas
"""

import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict
from app.models.membership import RoleEnum


class MembershipCreate(BaseModel):
    email: EmailStr
    role: RoleEnum = RoleEnum.VIEWER


class MembershipUpdate(BaseModel):
    role: RoleEnum


class MembershipRead(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    user_email: str
    user_full_name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

