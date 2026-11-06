"""
Pydantic Schemas for Incident Management, Event Logs, and Root Cause Diagnostics
"""

import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.models.incident import IncidentSeverityEnum, IncidentStatusEnum


class IncidentBase(BaseModel):
    title: str = Field(..., max_length=500, description="Summary title of the incident")
    description: Optional[str] = Field(None, description="Detailed incident description")
    severity: IncidentSeverityEnum = Field(
        default=IncidentSeverityEnum.P2_HIGH,
        description="Severity classification (P1_CRITICAL to P4_LOW)",
    )


class IncidentCreate(IncidentBase):
    service_id: uuid.UUID = Field(..., description="Target affected service UUID")


class IncidentUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    severity: Optional[IncidentSeverityEnum] = None
    status: Optional[IncidentStatusEnum] = None


class IncidentAcknowledgeRequest(BaseModel):
    note: Optional[str] = Field(None, description="Optional acknowledgement note")


class IncidentAssignRequest(BaseModel):
    assigned_to_user_id: uuid.UUID = Field(..., description="User ID to assign incident to")


class IncidentDiagnoseRequest(BaseModel):
    force_re_evaluation: bool = Field(
        default=False,
        description="Force execution of diagnosis rules even if already diagnosed",
    )


class IncidentEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    incident_id: uuid.UUID
    event_type: str
    message: str
    payload: Optional[Dict[str, Any]] = None
    created_at: datetime


class DiagnosisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    incident_id: uuid.UUID
    rule_name: str
    root_cause_hypothesis: str
    confidence_score: float
    evidence: Optional[Dict[str, Any]] = None
    recommended_action: str
    created_at: datetime


class IncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    workspace_id: uuid.UUID
    service_id: uuid.UUID
    incident_number: str
    title: str
    description: Optional[str] = None
    severity: str
    status: str
    assigned_to_user_id: Optional[uuid.UUID] = None
    detected_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    service_name: Optional[str] = None
    events: List[IncidentEventResponse] = []
    diagnoses: List[DiagnosisResponse] = []


class IncidentListResponse(BaseModel):
    items: List[IncidentResponse]
    total: int
    page: int
    size: int

