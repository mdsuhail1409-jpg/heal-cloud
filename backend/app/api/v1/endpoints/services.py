"""
Service Inventory & Monitoring API Endpoints (Tenant-Scoped)
"""

import uuid
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictException,
    EntityNotFoundException,
    ValidationException,
)
from app.core.deps import require_role, TenantContext
from app.core.ssrf import validate_target_url
from app.db.session import get_db
from app.models.organization import Workspace
from app.models.membership import RoleEnum
from app.models.service import (
    Service,
    ServiceEndpoint,
    MonitoringCheck,
    MetricSample,
    HealthStatusEnum,
)
from app.schemas.service import (
    ServiceCreate,
    ServiceUpdate,
    ServiceRead,
    ServiceEndpointCreate,
    ServiceEndpointRead,
    MetricSampleRead,
    HealthCheckResult,
)
from app.services.health_checker import execute_monitoring_check

router = APIRouter(
    prefix="/organizations/{org_id}/workspaces/{workspace_id}/services",
    tags=["Service Inventory & Monitoring"],
)


def _get_verified_workspace(org_id: uuid.UUID, workspace_id: uuid.UUID, db: Session) -> Workspace:
    """Verifies that the workspace belongs to the organization."""
    ws = (
        db.query(Workspace)
        .filter(Workspace.id == workspace_id, Workspace.organization_id == org_id)
        .first()
    )
    if not ws:
        raise EntityNotFoundException("Workspace", workspace_id)
    return ws


def _get_verified_service(
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
    service_id: uuid.UUID,
    db: Session,
) -> Service:
    """Verifies that the service exists and is strictly scoped to the workspace and organization."""
    srv = (
        db.query(Service)
        .filter(
            Service.id == service_id,
            Service.workspace_id == workspace_id,
            Service.organization_id == org_id,
        )
        .first()
    )
    if not srv:
        raise EntityNotFoundException("Service", service_id)
    return srv


@router.get(
    "",
    response_model=List[ServiceRead],
    status_code=status.HTTP_200_OK,
    summary="List Services in Workspace",
    description="Returns all registered services within the specified workspace. Requires VIEWER role or higher.",
)
def list_services(
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
    tenant_ctx: TenantContext = Depends(require_role(RoleEnum.VIEWER)),
    db: Session = Depends(get_db),
) -> List[ServiceRead]:
    _get_verified_workspace(org_id, workspace_id, db)
    services = (
        db.query(Service)
        .filter(Service.workspace_id == workspace_id, Service.organization_id == org_id)
        .order_by(Service.created_at.desc())
        .all()
    )
    return [ServiceRead.model_validate(s) for s in services]


@router.post(
    "",
    response_model=ServiceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register New Monitored Service",
    description="Registers a service and configures an initial HTTP health check. Requires RELIABILITY_ENGINEER or higher.",
)
def register_service(
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
    req: ServiceCreate,
    tenant_ctx: TenantContext = Depends(require_role(RoleEnum.RELIABILITY_ENGINEER)),
    db: Session = Depends(get_db),
) -> ServiceRead:
    _get_verified_workspace(org_id, workspace_id, db)

    # Check for duplicate service name in workspace
    existing = (
        db.query(Service)
        .filter(Service.workspace_id == workspace_id, Service.name == req.name)
        .first()
    )
    if existing:
        raise ConflictException(
            f"A service named '{req.name}' is already registered in this workspace.",
            details={"name": req.name},
        )

    # Create Service record
    service = Service(
        organization_id=org_id,
        workspace_id=workspace_id,
        name=req.name,
        description=req.description,
        health_status=HealthStatusEnum.UNKNOWN.value,
        consecutive_failures=0,
    )
    db.add(service)
    db.flush()

    # Create Service Endpoint
    endpoint = ServiceEndpoint(
        service_id=service.id,
        url=req.endpoint_url,
        method=req.method,
        expected_status_code=req.expected_status_code,
        timeout_ms=req.timeout_ms,
        headers={},
    )
    db.add(endpoint)
    db.flush()

    # Create Monitoring Check definition
    check = MonitoringCheck(
        service_id=service.id,
        endpoint_id=endpoint.id,
        interval_seconds=req.check_interval_seconds,
        consecutive_failure_threshold=req.consecutive_failure_threshold,
        is_enabled=True,
    )
    db.add(check)
    db.flush()

    db.refresh(service)
    return ServiceRead.model_validate(service)


@router.get(
    "/{service_id}",
    response_model=ServiceRead,
    status_code=status.HTTP_200_OK,
    summary="Get Service Dossier",
    description="Retrieves service details, configured endpoints, and monitoring configuration. Requires VIEWER role.",
)
def get_service(
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
    service_id: uuid.UUID,
    tenant_ctx: TenantContext = Depends(require_role(RoleEnum.VIEWER)),
    db: Session = Depends(get_db),
) -> ServiceRead:
    _get_verified_workspace(org_id, workspace_id, db)
    service = _get_verified_service(org_id, workspace_id, service_id, db)
    return ServiceRead.model_validate(service)


@router.put(
    "/{service_id}",
    response_model=ServiceRead,
    status_code=status.HTTP_200_OK,
    summary="Update Service Metadata",
    description="Updates service name or description. Requires RELIABILITY_ENGINEER or higher.",
)
def update_service(
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
    service_id: uuid.UUID,
    req: ServiceUpdate,
    tenant_ctx: TenantContext = Depends(require_role(RoleEnum.RELIABILITY_ENGINEER)),
    db: Session = Depends(get_db),
) -> ServiceRead:
    _get_verified_workspace(org_id, workspace_id, db)
    service = _get_verified_service(org_id, workspace_id, service_id, db)

    if req.name is not None and req.name != service.name:
        existing = (
            db.query(Service)
            .filter(
                Service.workspace_id == workspace_id,
                Service.name == req.name,
                Service.id != service.id,
            )
            .first()
        )
        if existing:
            raise ConflictException(f"A service named '{req.name}' already exists in this workspace.")
        service.name = req.name

    if req.description is not None:
        service.description = req.description

    db.add(service)
    return ServiceRead.model_validate(service)


@router.delete(
    "/{service_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Service",
    description="Permanently removes a service and its associated endpoints and monitoring history. Requires ORG_ADMIN.",
)
def delete_service(
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
    service_id: uuid.UUID,
    tenant_ctx: TenantContext = Depends(require_role(RoleEnum.ORG_ADMIN)),
    db: Session = Depends(get_db),
) -> dict:
    _get_verified_workspace(org_id, workspace_id, db)
    service = _get_verified_service(org_id, workspace_id, service_id, db)

    db.delete(service)
    return {
        "message": f"Service '{service.name}' deleted successfully.",
        "service_id": str(service_id),
    }


@router.post(
    "/{service_id}/endpoints",
    response_model=ServiceEndpointRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add Service Endpoint",
    description="Registers an additional HTTP endpoint for an existing service.",
)
def add_service_endpoint(
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
    service_id: uuid.UUID,
    req: ServiceEndpointCreate,
    tenant_ctx: TenantContext = Depends(require_role(RoleEnum.RELIABILITY_ENGINEER)),
    db: Session = Depends(get_db),
) -> ServiceEndpointRead:
    _get_verified_workspace(org_id, workspace_id, db)
    service = _get_verified_service(org_id, workspace_id, service_id, db)

    endpoint = ServiceEndpoint(
        service_id=service.id,
        url=req.url,
        method=req.method,
        expected_status_code=req.expected_status_code,
        timeout_ms=req.timeout_ms,
        headers=req.headers or {},
    )
    db.add(endpoint)
    db.flush()

    return ServiceEndpointRead.model_validate(endpoint)


@router.post(
    "/{service_id}/checks/run",
    response_model=HealthCheckResult,
    status_code=status.HTTP_200_OK,
    summary="Trigger On-Demand Health Check Probe",
    description="Executes a live health check probe against the service's primary endpoint. Requires RELIABILITY_ENGINEER.",
)
def run_service_health_check(
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
    service_id: uuid.UUID,
    tenant_ctx: TenantContext = Depends(require_role(RoleEnum.RELIABILITY_ENGINEER)),
    db: Session = Depends(get_db),
) -> HealthCheckResult:
    _get_verified_workspace(org_id, workspace_id, db)
    service = _get_verified_service(org_id, workspace_id, service_id, db)

    check = (
        db.query(MonitoringCheck)
        .filter(MonitoringCheck.service_id == service.id)
        .first()
    )
    if not check:
        raise ValidationException("Service has no configured monitoring checks.")

    sample = execute_monitoring_check(check.id, db=db)
    db.refresh(service)

    return HealthCheckResult(
        service_id=service.id,
        service_name=service.name,
        health_status=service.health_status,
        status_code=sample.status_code,
        response_time_ms=sample.response_time_ms,
        consecutive_failures=service.consecutive_failures,
        is_successful=sample.is_successful,
        error_message=sample.error_message,
        checked_at=sample.timestamp.isoformat(),
    )


@router.get(
    "/{service_id}/metrics",
    response_model=List[MetricSampleRead],
    status_code=status.HTTP_200_OK,
    summary="Get Service Metric History",
    description="Returns chronological health check samples, response times, and failure records. Requires VIEWER role.",
)
def get_service_metric_history(
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
    service_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=500),
    tenant_ctx: TenantContext = Depends(require_role(RoleEnum.VIEWER)),
    db: Session = Depends(get_db),
) -> List[MetricSampleRead]:
    _get_verified_workspace(org_id, workspace_id, db)
    _get_verified_service(org_id, workspace_id, service_id, db)

    samples = (
        db.query(MetricSample)
        .filter(MetricSample.service_id == service_id)
        .order_by(MetricSample.timestamp.desc())
        .limit(limit)
        .all()
    )

    return [MetricSampleRead.model_validate(s) for s in samples]

