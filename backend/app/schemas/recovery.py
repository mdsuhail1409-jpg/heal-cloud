"""
Pydantic Schemas for Recovery Policies, Simulator Executions, and Approvals
"""

import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.models.recovery import (
    AllowlistedActionEnum,
    RecoveryStatusEnum,
    ApprovalDecisionEnum,
    RiskTierEnum,
)


class RecoveryPolicyBase(BaseModel):
    name: str = Field(..., max_length=255)
    trigger_condition: str = Field(..., max_length=100)
    action: AllowlistedActionEnum = Field(default=AllowlistedActionEnum.SIMULATE_RESTART)
    requires_approval: bool = Field(default=False)
    max_retries: int = Field(default=2, ge=1, le=5)
    cooldown_seconds: int = Field(default=300, ge=10, le=3600)
    timeout_seconds: int = Field(default=60, ge=5, le=300)
    service_id: Optional[uuid.UUID] = None


class RecoveryPolicyCreate(RecoveryPolicyBase):
    pass


class RecoveryPolicyUpdate(BaseModel):
    name: Optional[str] = None
    is_enabled: Optional[bool] = None
    requires_approval: Optional[bool] = None
    cooldown_seconds: Optional[int] = None
    max_retries: Optional[int] = None


class RecoveryPolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    workspace_id: uuid.UUID
    service_id: Optional[uuid.UUID] = None
    service_name: Optional[str] = None
    name: str
    trigger_condition: str
    action: str
    requires_approval: bool
    max_retries: int
    cooldown_seconds: int
    timeout_seconds: int
    is_enabled: bool
    created_at: datetime
    updated_at: datetime


class ApprovalDecideRequest(BaseModel):
    decision: ApprovalDecisionEnum
    reason: Optional[str] = None


class ApprovalRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    execution_id: Optional[uuid.UUID] = None
    incident_id: uuid.UUID
    incident_number: Optional[str] = None
    service_id: uuid.UUID
    service_name: Optional[str] = None
    proposed_action: str
    risk_tier: str
    blast_radius: str
    status: str
    decision_reason: Optional[str] = None
    requested_by_user_id: Optional[uuid.UUID] = None
    requested_by: Optional[str] = None
    decided_by_user_id: Optional[uuid.UUID] = None
    decided_by: Optional[str] = None
    requested_at: datetime
    decided_at: Optional[datetime] = None


class RecoveryExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    workspace_id: uuid.UUID
    incident_id: uuid.UUID
    incident_number: Optional[str] = None
    policy_id: Optional[uuid.UUID] = None
    policy_name: Optional[str] = None
    service_id: uuid.UUID
    service_name: Optional[str] = None
    action_taken: str
    status: str
    execution_output: Optional[str] = None
    duration_ms: Optional[int] = None
    verification_passed: Optional[bool] = None
    failure_reason: Optional[str] = None
    requested_by_user_id: Optional[uuid.UUID] = None
    started_at: datetime
    completed_at: Optional[datetime] = None


class RemediateTriggerRequest(BaseModel):
    policy_id: Optional[uuid.UUID] = None
    action: Optional[AllowlistedActionEnum] = None
    note: Optional[str] = None

