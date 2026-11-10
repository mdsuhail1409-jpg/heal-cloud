"""
Recovery Policies, Approvals & Controlled Simulator Endpoints (Tenant-Scoped)
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
from app.models.incident import Incident
from app.models.recovery import (
    RecoveryPolicy,
    RecoveryExecution,
    ApprovalRequest,
    AllowlistedActionEnum,
    ApprovalDecisionEnum,
    RiskTierEnum,
)
from app.schemas.recovery import (
    RecoveryPolicyCreate,
    RecoveryPolicyUpdate,
    RecoveryPolicyResponse,
    ApprovalDecideRequest,
    ApprovalRequestResponse,
    RecoveryExecutionResponse,
    RemediateTriggerRequest,
)
from app.services.recovery_simulator import (
    execute_recovery_simulation,
    log_audit_event,
)

router = APIRouter(
    prefix="/organizations/{org_id}/workspaces/{workspace_id}",
    tags=["Self-Healing Recovery & Approvals"],
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


# --- Recovery Policies ---
@router.get("/recovery-policies", response_model=List[RecoveryPolicyResponse])
def list_recovery_policies(
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    _get_verified_workspace(org_id, workspace_id, db)
    policies = (
        db.query(RecoveryPolicy)
        .filter(
            RecoveryPolicy.organization_id == org_id,
            RecoveryPolicy.workspace_id == workspace_id,
        )
        .order_by(desc(RecoveryPolicy.created_at))
        .all()
    )
    return [
        RecoveryPolicyResponse(
            id=p.id,
            organization_id=p.organization_id,
            workspace_id=p.workspace_id,
            service_id=p.service_id,
            service_name=p.service.name if p.service else None,
            name=p.name,
            trigger_condition=p.trigger_condition,
            action=p.action,
            requires_approval=p.requires_approval,
            max_retries=p.max_retries,
            cooldown_seconds=p.cooldown_seconds,
            timeout_seconds=p.timeout_seconds,
            is_enabled=p.is_enabled,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in policies
    ]


@router.post(
    "/recovery-policies",
    response_model=RecoveryPolicyResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_recovery_policy(
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
    data: RecoveryPolicyCreate,
    tenant_ctx: TenantContext = Depends(require_role(RoleEnum.RELIABILITY_ENGINEER)),
    db: Session = Depends(get_db),
):
    _get_verified_workspace(org_id, workspace_id, db)

    if data.service_id:
        svc = (
            db.query(Service)
            .filter(
                Service.id == data.service_id,
                Service.organization_id == org_id,
                Service.workspace_id == workspace_id,
            )
            .first()
        )
        if not svc:
            raise EntityNotFoundException("Service", data.service_id)

    policy = RecoveryPolicy(
        organization_id=org_id,
        workspace_id=workspace_id,
        service_id=data.service_id,
        name=data.name,
        trigger_condition=data.trigger_condition,
        action=data.action.value,
        requires_approval=data.requires_approval,
        max_retries=data.max_retries,
        cooldown_seconds=data.cooldown_seconds,
        timeout_seconds=data.timeout_seconds,
        is_enabled=True,
    )
    db.add(policy)
    db.flush()

    log_audit_event(
        db=db,
        organization_id=org_id,
        user=tenant_ctx.user,
        action="POLICY_CREATED",
        resource_type="RecoveryPolicy",
        resource_id=str(policy.id),
        payload={"name": policy.name, "action": policy.action},
    )

    db.commit()
    db.refresh(policy)

    return RecoveryPolicyResponse(
        id=policy.id,
        organization_id=policy.organization_id,
        workspace_id=policy.workspace_id,
        service_id=policy.service_id,
        service_name=policy.service.name if policy.service else None,
        name=policy.name,
        trigger_condition=policy.trigger_condition,
        action=policy.action,
        requires_approval=policy.requires_approval,
        max_retries=policy.max_retries,
        cooldown_seconds=policy.cooldown_seconds,
        timeout_seconds=policy.timeout_seconds,
        is_enabled=policy.is_enabled,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
    )


@router.patch("/recovery-policies/{policy_id}", response_model=RecoveryPolicyResponse)
def update_recovery_policy(
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
    policy_id: uuid.UUID,
    data: RecoveryPolicyUpdate,
    tenant_ctx: TenantContext = Depends(require_role(RoleEnum.RELIABILITY_ENGINEER)),
    db: Session = Depends(get_db),
):
    _get_verified_workspace(org_id, workspace_id, db)
    policy = (
        db.query(RecoveryPolicy)
        .filter(
            RecoveryPolicy.id == policy_id,
            RecoveryPolicy.organization_id == org_id,
            RecoveryPolicy.workspace_id == workspace_id,
        )
        .first()
    )
    if not policy:
        raise EntityNotFoundException("RecoveryPolicy", policy_id)

    if data.name is not None:
        policy.name = data.name
    if data.is_enabled is not None:
        policy.is_enabled = data.is_enabled
    if data.requires_approval is not None:
        policy.requires_approval = data.requires_approval
    if data.cooldown_seconds is not None:
        policy.cooldown_seconds = data.cooldown_seconds
    if data.max_retries is not None:
        policy.max_retries = data.max_retries

    db.add(policy)
    db.commit()
    db.refresh(policy)

    return RecoveryPolicyResponse(
        id=policy.id,
        organization_id=policy.organization_id,
        workspace_id=policy.workspace_id,
        service_id=policy.service_id,
        service_name=policy.service.name if policy.service else None,
        name=policy.name,
        trigger_condition=policy.trigger_condition,
        action=policy.action,
        requires_approval=policy.requires_approval,
        max_retries=policy.max_retries,
        cooldown_seconds=policy.cooldown_seconds,
        timeout_seconds=policy.timeout_seconds,
        is_enabled=policy.is_enabled,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
    )


# --- Approval Requests ---
@router.get("/approvals", response_model=List[ApprovalRequestResponse])
def list_approval_requests(
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    _get_verified_workspace(org_id, workspace_id, db)
    approvals = (
        db.query(ApprovalRequest)
        .filter(
            ApprovalRequest.organization_id == org_id,
            ApprovalRequest.workspace_id == workspace_id,
        )
        .order_by(desc(ApprovalRequest.requested_at))
        .all()
    )
    return [
        ApprovalRequestResponse(
            id=a.id,
            execution_id=a.execution_id,
            incident_id=a.incident_id,
            incident_number=a.incident.incident_number if a.incident else None,
            service_id=a.service_id,
            service_name=a.service.name if a.service else None,
            proposed_action=a.proposed_action,
            risk_tier=a.risk_tier,
            blast_radius=a.blast_radius,
            status=a.status,
            decision_reason=a.decision_reason,
            requested_by_user_id=a.requested_by_user_id,
            requested_by=a.requested_by.email if a.requested_by else "Autonomous System",
            decided_by_user_id=a.decided_by_user_id,
            decided_by=a.decided_by.email if a.decided_by else None,
            requested_at=a.requested_at,
            decided_at=a.decided_at,
        )
        for a in approvals
    ]


@router.post("/approvals/{approval_id}/decide", response_model=ApprovalRequestResponse)
def decide_approval_request(
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
    approval_id: uuid.UUID,
    data: ApprovalDecideRequest,
    tenant_ctx: TenantContext = Depends(require_role(RoleEnum.RELIABILITY_ENGINEER)),
    db: Session = Depends(get_db),
):
    _get_verified_workspace(org_id, workspace_id, db)
    approval = (
        db.query(ApprovalRequest)
        .filter(
            ApprovalRequest.id == approval_id,
            ApprovalRequest.organization_id == org_id,
            ApprovalRequest.workspace_id == workspace_id,
        )
        .first()
    )
    if not approval:
        raise EntityNotFoundException("ApprovalRequest", approval_id)

    if approval.status != ApprovalDecisionEnum.PENDING.value:
        raise ValidationException("Approval request has already been decided.")

    now = datetime.now(timezone.utc)
    approval.status = data.decision.value
    approval.decision_reason = data.reason
    approval.decided_by_user_id = tenant_ctx.user.id
    approval.decided_at = now
    db.add(approval)

    log_audit_event(
        db=db,
        organization_id=org_id,
        user=tenant_ctx.user,
        action=f"APPROVAL_{data.decision.value}",
        resource_type="ApprovalRequest",
        resource_id=str(approval.id),
        payload={"action": approval.proposed_action, "reason": data.reason},
    )

    # If APPROVED, execute the recovery simulation immediately!
    if data.decision == ApprovalDecisionEnum.APPROVED:
        incident = db.query(Incident).filter(Incident.id == approval.incident_id).first()
        if incident:
            exec_record = execute_recovery_simulation(
                db=db,
                incident=incident,
                action=approval.proposed_action,
                operator=tenant_ctx.user,
            )
            approval.execution_id = exec_record.id
            db.add(approval)

    db.commit()
    db.refresh(approval)

    return ApprovalRequestResponse(
        id=approval.id,
        execution_id=approval.execution_id,
        incident_id=approval.incident_id,
        incident_number=approval.incident.incident_number if approval.incident else None,
        service_id=approval.service_id,
        service_name=approval.service.name if approval.service else None,
        proposed_action=approval.proposed_action,
        risk_tier=approval.risk_tier,
        blast_radius=approval.blast_radius,
        status=approval.status,
        decision_reason=approval.decision_reason,
        requested_by_user_id=approval.requested_by_user_id,
        requested_by=approval.requested_by.email if approval.requested_by else "Autonomous System",
        decided_by_user_id=approval.decided_by_user_id,
        decided_by=approval.decided_by.email if approval.decided_by else None,
        requested_at=approval.requested_at,
        decided_at=approval.decided_at,
    )


# --- Recovery Executions History ---
@router.get("/recovery-executions", response_model=List[RecoveryExecutionResponse])
def list_recovery_executions(
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    _get_verified_workspace(org_id, workspace_id, db)
    executions = (
        db.query(RecoveryExecution)
        .filter(
            RecoveryExecution.organization_id == org_id,
            RecoveryExecution.workspace_id == workspace_id,
        )
        .order_by(desc(RecoveryExecution.started_at))
        .all()
    )
    return [
        RecoveryExecutionResponse(
            id=e.id,
            organization_id=e.organization_id,
            workspace_id=e.workspace_id,
            incident_id=e.incident_id,
            incident_number=e.incident.incident_number if e.incident else None,
            policy_id=e.policy_id,
            policy_name=e.policy.name if e.policy else "Manual Remediation",
            service_id=e.service_id,
            service_name=e.service.name if e.service else None,
            action_taken=e.action_taken,
            status=e.status,
            execution_output=e.execution_output,
            duration_ms=e.duration_ms,
            verification_passed=e.verification_passed,
            failure_reason=e.failure_reason,
            requested_by_user_id=e.requested_by_user_id,
            started_at=e.started_at,
            completed_at=e.completed_at,
        )
        for e in executions
    ]


# --- Trigger Remediation for an Incident ---
@router.post(
    "/incidents/{incident_id}/remediate",
    response_model=RecoveryExecutionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def trigger_remediation(
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
    incident_id: uuid.UUID,
    data: RemediateTriggerRequest = RemediateTriggerRequest(),
    tenant_ctx: TenantContext = Depends(require_role(RoleEnum.RELIABILITY_ENGINEER)),
    db: Session = Depends(get_db),
):
    _get_verified_workspace(org_id, workspace_id, db)
    incident = (
        db.query(Incident)
        .filter(
            Incident.id == incident_id,
            Incident.organization_id == org_id,
            Incident.workspace_id == workspace_id,
        )
        .first()
    )
    if not incident:
        raise EntityNotFoundException("Incident", incident_id)

    # Check for matching or specified policy
    policy = None
    if data.policy_id:
        policy = db.query(RecoveryPolicy).filter(RecoveryPolicy.id == data.policy_id).first()
    else:
        # Match policy by service or trigger condition
        policy = (
            db.query(RecoveryPolicy)
            .filter(
                RecoveryPolicy.workspace_id == workspace_id,
                RecoveryPolicy.is_enabled == True,
            )
            .first()
        )

    # If policy requires approval, queue an ApprovalRequest
    if policy and policy.requires_approval:
        approval = ApprovalRequest(
            organization_id=org_id,
            workspace_id=workspace_id,
            incident_id=incident.id,
            service_id=incident.service_id,
            proposed_action=policy.action,
            risk_tier=RiskTierEnum.TIER_2_MEDIUM.value,
            blast_radius=f"1 Service ({incident.service.name if incident.service else 'target'})",
            status=ApprovalDecisionEnum.PENDING.value,
            requested_by_user_id=tenant_ctx.user.id,
            requested_at=datetime.now(timezone.utc),
        )
        db.add(approval)
        db.commit()
        db.refresh(approval)

        return RecoveryExecutionResponse(
            id=uuid.uuid4(),
            organization_id=org_id,
            workspace_id=workspace_id,
            incident_id=incident.id,
            incident_number=incident.incident_number,
            service_id=incident.service_id,
            service_name=incident.service.name if incident.service else None,
            action_taken=policy.action,
            status="QUEUED",
            execution_output="Awaiting Human-in-the-Loop (HITL) approval before execution.",
            requested_by_user_id=tenant_ctx.user.id,
            started_at=datetime.now(timezone.utc),
        )

    # Execute simulation directly
    exec_record = execute_recovery_simulation(
        db=db,
        incident=incident,
        policy=policy,
        action=data.action.value if data.action else (policy.action if policy else None),
        operator=tenant_ctx.user,
    )
    db.commit()
    db.refresh(exec_record)

    return RecoveryExecutionResponse(
        id=exec_record.id,
        organization_id=exec_record.organization_id,
        workspace_id=exec_record.workspace_id,
        incident_id=exec_record.incident_id,
        incident_number=exec_record.incident.incident_number if exec_record.incident else None,
        policy_id=exec_record.policy_id,
        policy_name=exec_record.policy.name if exec_record.policy else "Manual Trigger",
        service_id=exec_record.service_id,
        service_name=exec_record.service.name if exec_record.service else None,
        action_taken=exec_record.action_taken,
        status=exec_record.status,
        execution_output=exec_record.execution_output,
        duration_ms=exec_record.duration_ms,
        verification_passed=exec_record.verification_passed,
        failure_reason=exec_record.failure_reason,
        requested_by_user_id=exec_record.requested_by_user_id,
        started_at=exec_record.started_at,
        completed_at=exec_record.completed_at,
    )

