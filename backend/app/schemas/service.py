"""
Service Inventory and Monitoring Pydantic Validation Schemas
"""

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict

from app.core.ssrf import validate_target_url
from app.models.service import HealthStatusEnum


class ServiceEndpointCreate(BaseModel):
    url: str
    method: str = Field("GET", pattern="^(GET|POST|HEAD|OPTIONS)$")
    expected_status_code: int = Field(200, ge=100, le=599)
    timeout_ms: int = Field(5000, ge=500, le=30000)
    headers: Optional[Dict[str, str]] = None

    @field_validator("url")
    @classmethod
    def validate_endpoint_url(cls, v: str) -> str:
        return validate_target_url(v)


class ServiceEndpointRead(BaseModel):
    id: uuid.UUID
    service_id: uuid.UUID
    url: str
    method: str
    expected_status_code: int
    timeout_ms: int
    headers: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MonitoringCheckCreate(BaseModel):
    endpoint_id: Optional[uuid.UUID] = None
    interval_seconds: int = Field(30, ge=5, le=3600)
    consecutive_failure_threshold: int = Field(3, ge=1, le=20)
    is_enabled: bool = True


class MonitoringCheckRead(BaseModel):
    id: uuid.UUID
    service_id: uuid.UUID
    endpoint_id: uuid.UUID
    interval_seconds: int
    consecutive_failure_threshold: int
    is_enabled: bool
    last_checked_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ServiceCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    endpoint_url: str
    method: str = Field("GET", pattern="^(GET|POST|HEAD|OPTIONS)$")
    expected_status_code: int = Field(200, ge=100, le=599)
    timeout_ms: int = Field(5000, ge=500, le=30000)
    check_interval_seconds: int = Field(30, ge=5, le=3600)
    consecutive_failure_threshold: int = Field(3, ge=1, le=20)

    @field_validator("endpoint_url")
    @classmethod
    def validate_endpoint_url(cls, v: str) -> str:
        return validate_target_url(v)


class ServiceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None


class ServiceRead(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: Optional[str] = None
    health_status: str
    consecutive_failures: int
    last_success_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None
    created_at: datetime
    endpoints: List[ServiceEndpointRead] = []
    checks: List[MonitoringCheckRead] = []

    model_config = ConfigDict(from_attributes=True)


class MetricSampleRead(BaseModel):
    id: uuid.UUID
    service_id: uuid.UUID
    check_id: uuid.UUID
    timestamp: datetime
    status_code: Optional[int] = None
    response_time_ms: float
    is_successful: bool
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class HealthCheckResult(BaseModel):
    service_id: uuid.UUID
    service_name: str
    health_status: str
    status_code: Optional[int] = None
    response_time_ms: float
    consecutive_failures: int
    is_successful: bool
    error_message: Optional[str] = None
    checked_at: str

