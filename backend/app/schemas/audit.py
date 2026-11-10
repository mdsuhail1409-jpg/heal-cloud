"""
Pydantic Schemas for Immutable Audit Trail
"""

import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    user_email: str
    action: str
    resource_type: str
    resource_id: str
    payload: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    created_at: datetime

