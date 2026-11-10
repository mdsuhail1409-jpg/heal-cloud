"""
Incident Detection, Management & Diagnosis API Endpoints (Tenant-Scoped)
"""

import uuid
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.exceptions import (
    EntityNotFoundException,
    ValidationException,
    ForbiddenException,
)
from app.core.deps import require_role, get_tenant_context, TenantContext
from app.db.session import get_db
from app.models.organization import Workspace
from app.models.membership import RoleEnum
from app.models.service import Service
from app.models.user import User
from app.models.incident import (
    Incident,
    IncidentEvent,
    Diagnosis,
    IncidentSeverityEnum,
    IncidentStatusEnum,
    IncidentEventTypeEnum,
)
from app.schemas.incident import (
    IncidentCreate,
    IncidentUpdate,
    IncidentAcknowledgeRequest,
    IncidentAssignRequest,
    IncidentDiagnoseRequest,
    IncidentEventResponse,
    DiagnosisResponse,
    IncidentResponse,
    IncidentListResponse,
)
from app.services.detection_engine import (
    generate_incident_number,
    run_explainable_diagnosis,
)
from app.services.recovery_simulator import log_audit_event

router = APIRouter(
    prefix="/organizations/{org_id}/workspaces/{workspace_id}/incidents",
    tags=["Incidents & Diagnostics"],
)


def _get_verified_workspace(org_id: uuid.UUID, workspace_id: uuid.UUID, db: Session) -> Workspace:
    ws = (
        db.query(Workspace)
        .filter(Workspace.id == workspace_id, Workspace.organization_id == org_id)
        .first()
    )
    if not ws:
        raise EntityNotFoundException("Workspace", workspace_id)
    return ws


def _get_verified_incident(
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
    incident_id: uuid.UUID,
    db: Session,
) -> Incident:
    inc = (
        db.query(Incident)
        .filter(
            Incident.id == incident_id,
            Incident.organization_id == org_id,
            Incident.workspace_id == workspace_id,
        )
        .first()
    )
    if not inc:
        raise EntityNotFoundException("Incident", incident_id)
    return inc


def _serialize_incident(inc: Incident) -> IncidentResponse:
    return IncidentResponse(
        id=inc.id,
        organization_id=inc.organization_id,
        workspace_id=inc.workspace_id,
        service_id=inc.service_id,
        incident_number=inc.incident_number,
        title=inc.title,
        description=inc.description,
        severity=inc.severity,
        status=inc.status,
        assigned_to_user_id=inc.assigned_to_user_id,
        detected_at=inc.detected_at,
        acknowledged_at=inc.acknowledged_at,
        resolved_at=inc.resolved_at,
        created_at=inc.created_at,
        updated_at=inc.updated_at,
        service_name=inc.service.name if inc.service else None,
        events=[IncidentEventResponse.model_validate(e) for e in inc.events],
        diagnoses=[DiagnosisResponse.model_validate(d) for d in inc.diagnoses],
    )


@router.get("", response_model=IncidentListResponse)
def list_incidents(
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
    status: Optional[str] = Query(None, description="Filter by status (OPEN, ACKNOWLEDGED, RESOLVED, etc.)"),
    severity: Optional[str] = Query(None, description="Filter by severity (P1_CRITICAL, P2_HIGH, etc.)"),
    service_id: Optional[uuid.UUID] = Query(None, description="Filter by affected service ID"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Lists all incidents within a workspace with optional status, severity, and service filters.
    Accessible to all authorized workspace members.
    """
    _get_verified_workspace(org_id, workspace_id, db)

    query = db.query(Incident).filter(
        Incident.organization_id == org_id,
        Incident.workspace_id == workspace_id,
    )

    if status:
        query = query.filter(Incident.status == status.upper())
    if severity:
        query = query.filter(Incident.severity == severity.upper())
    if service_id:
        query = query.filter(Incident.service_id == service_id)

    total = query.count()
    incidents = (
        query.order_by(desc(Incident.detected_at))
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    items = [_serialize_incident(inc) for inc in incidents]
    return IncidentListResponse(items=items, total=total, page=page, size=size)


@router.post("", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
def create_incident(
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
    data: IncidentCreate,
    tenant_ctx: TenantContext = Depends(require_role(RoleEnum.RELIABILITY_ENGINEER)),
    db: Session = Depends(get_db),
):
    """
    Manually creates an incident within a workspace for an affected service.
    Requires RELIABILITY_ENGINEER or higher.
    """
    _get_verified_workspace(org_id, workspace_id, db)

    service = (
        db.query(Service)
        .filter(
            Service.id == data.service_id,
            Service.organization_id == org_id,
            Service.workspace_id == workspace_id,
        )
        .first()
    )
    if not service:
        raise EntityNotFoundException("Service", data.service_id)

    now = datetime.now(timezone.utc)
    incident_number = generate_incident_number(db)

    incident = Incident(
        organization_id=org_id,
        workspace_id=workspace_id,
        service_id=data.service_id,
        incident_number=incident_number,
        title=data.title,
        description=data.description,
        severity=data.severity.value,
        status=IncidentStatusEnum.OPEN.value,
        detected_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(incident)
    db.flush()

    # Initial event
    event = IncidentEvent(
        incident_id=incident.id,
        event_type=IncidentEventTypeEnum.DETECTED.value,
        message=f"Incident manually opened by {tenant_ctx.user.email}: {data.title}",
        payload={"reporter_user_id": str(tenant_ctx.user.id), "initial_severity": data.severity.value},
        created_at=now,
    )
    db.add(event)

    # Initial explainable diagnosis run
    run_explainable_diagnosis(db, incident.id)

    log_audit_event(
        db=db,
        organization_id=org_id,
        user=tenant_ctx.user,
        action="INCIDENT_DECLARED",
        resource_type="Incident",
        resource_id=str(incident.id),
        payload={"incident_number": incident.incident_number, "title": incident.title},
    )

    db.commit()
    db.refresh(incident)
    return _serialize_incident(incident)


@router.get("/{incident_id}", response_model=IncidentResponse)
def get_incident(
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
    incident_id: uuid.UUID,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """
    Retrieves full incident dossier including service metadata, chronological event log,
    and root cause diagnostic history.
    """
    _get_verified_workspace(org_id, workspace_id, db)
    incident = _get_verified_incident(org_id, workspace_id, incident_id, db)
    return _serialize_incident(incident)


@router.post("/{incident_id}/acknowledge", response_model=IncidentResponse)
def acknowledge_incident(
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
    incident_id: uuid.UUID,
    body: IncidentAcknowledgeRequest = IncidentAcknowledgeRequest(),
    tenant_ctx: TenantContext = Depends(require_role(RoleEnum.RELIABILITY_ENGINEER)),
    db: Session = Depends(get_db),
):
    """
    Acknowledges an open incident, setting status to ACKNOWLEDGED and recording operator identity.
    Requires RELIABILITY_ENGINEER or higher.
    """
    _get_verified_workspace(org_id, workspace_id, db)
    incident = _get_verified_incident(org_id, workspace_id, incident_id, db)

    now = datetime.now(timezone.utc)
    incident.status = IncidentStatusEnum.ACKNOWLEDGED.value
    incident.acknowledged_at = now
    incident.updated_at = now

    event = IncidentEvent(
        incident_id=incident.id,
        event_type=IncidentEventTypeEnum.ACKNOWLEDGED.value,
        message=f"Incident acknowledged by {tenant_ctx.user.email}." + (f" Note: {body.note}" if body.note else ""),
        payload={"acknowledged_by": str(tenant_ctx.user.id), "note": body.note},
        created_at=now,
    )
    db.add(event)
    db.add(incident)

    log_audit_event(
        db=db,
        organization_id=org_id,
        user=tenant_ctx.user,
        action="INCIDENT_ACKNOWLEDGED",
        resource_type="Incident",
        resource_id=str(incident.id),
        payload={"incident_number": incident.incident_number, "note": body.note},
    )

    db.commit()
    db.refresh(incident)

    return _serialize_incident(incident)


@router.post("/{incident_id}/assign", response_model=IncidentResponse)
def assign_incident(
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
    incident_id: uuid.UUID,
    body: IncidentAssignRequest,
    tenant_ctx: TenantContext = Depends(require_role(RoleEnum.RELIABILITY_ENGINEER)),
    db: Session = Depends(get_db),
):
    """
    Assigns an incident to an engineer.
    Requires RELIABILITY_ENGINEER or higher.
    """
    _get_verified_workspace(org_id, workspace_id, db)
    incident = _get_verified_incident(org_id, workspace_id, incident_id, db)

    assignee = db.query(User).filter(User.id == body.assigned_to_user_id).first()
    if not assignee:
        raise EntityNotFoundException("User", body.assigned_to_user_id)

    now = datetime.now(timezone.utc)
    incident.assigned_to_user_id = assignee.id
    incident.updated_at = now

    event = IncidentEvent(
        incident_id=incident.id,
        event_type=IncidentEventTypeEnum.ASSIGNED.value,
        message=f"Incident assigned to {assignee.full_name or assignee.email} by {tenant_ctx.user.email}.",
        payload={"assigned_to": str(assignee.id), "assigned_by": str(tenant_ctx.user.id)},
        created_at=now,
    )
    db.add(event)
    db.add(incident)

    log_audit_event(
        db=db,
        organization_id=org_id,
        user=tenant_ctx.user,
        action="INCIDENT_ASSIGNED",
        resource_type="Incident",
        resource_id=str(incident.id),
        payload={"incident_number": incident.incident_number, "assigned_to": str(assignee.id)},
    )

    db.commit()
    db.refresh(incident)

    return _serialize_incident(incident)


@router.patch("/{incident_id}/status", response_model=IncidentResponse)
def update_incident_status(
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
    incident_id: uuid.UUID,
    data: IncidentUpdate,
    tenant_ctx: TenantContext = Depends(require_role(RoleEnum.RELIABILITY_ENGINEER)),
    db: Session = Depends(get_db),
):
    """
    Updates incident status or severity, validating legal state transitions.
    Requires RELIABILITY_ENGINEER or higher.
    """
    _get_verified_workspace(org_id, workspace_id, db)
    incident = _get_verified_incident(org_id, workspace_id, incident_id, db)

    now = datetime.now(timezone.utc)
    old_status = incident.status

    if data.title is not None:
        incident.title = data.title
    if data.description is not None:
        incident.description = data.description
    if data.severity is not None:
        incident.severity = data.severity.value

    if data.status is not None and data.status.value != old_status:
        new_status = data.status.value

        # Legal state transition check
        if old_status == IncidentStatusEnum.CLOSED.value and new_status != IncidentStatusEnum.OPEN.value:
            raise ValidationException("A CLOSED incident can only transition to OPEN (reopened).")

        incident.status = new_status
        if new_status == IncidentStatusEnum.RESOLVED.value:
            incident.resolved_at = now
        elif new_status == IncidentStatusEnum.OPEN.value and old_status == IncidentStatusEnum.RESOLVED.value:
            incident.resolved_at = None

        event = IncidentEvent(
            incident_id=incident.id,
            event_type=IncidentEventTypeEnum.STATUS_CHANGED.value,
            message=f"Incident status changed from {old_status} to {new_status} by {tenant_ctx.user.email}.",
            payload={"old_status": old_status, "new_status": new_status, "changed_by": str(tenant_ctx.user.id)},
            created_at=now,
        )
        db.add(event)

    incident.updated_at = now
    db.add(incident)
    db.commit()
    db.refresh(incident)

    return _serialize_incident(incident)


@router.post("/{incident_id}/diagnose", response_model=DiagnosisResponse)
def trigger_diagnosis(
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
    incident_id: uuid.UUID,
    body: IncidentDiagnoseRequest = IncidentDiagnoseRequest(),
    tenant_ctx: TenantContext = Depends(require_role(RoleEnum.RELIABILITY_ENGINEER)),
    db: Session = Depends(get_db),
):
    """
    Runs an on-demand explainable root-cause diagnosis evaluation.
    Requires RELIABILITY_ENGINEER or higher.
    """
    _get_verified_workspace(org_id, workspace_id, db)
    incident = _get_verified_incident(org_id, workspace_id, incident_id, db)

    diagnosis = run_explainable_diagnosis(
        db=db,
        incident_id=incident.id,
        force_re_evaluation=body.force_re_evaluation,
    )
    db.commit()
    db.refresh(diagnosis)

    return DiagnosisResponse.model_validate(diagnosis)

