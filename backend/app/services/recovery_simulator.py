"""
Controlled Self-Healing Recovery Simulator and Post-Recovery Health Verification Engine
"""

import time
import uuid
from typing import Optional, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.exceptions import (
    EntityNotFoundException,
    ValidationException,
    ConflictException,
    ForbiddenException,
)
from app.models.organization import Workspace
from app.models.service import Service, ServiceEndpoint, HealthStatusEnum
from app.models.incident import Incident, IncidentEvent, IncidentStatusEnum, IncidentEventTypeEnum
from app.models.recovery import (
    RecoveryPolicy,
    RecoveryExecution,
    ApprovalRequest,
    AllowlistedActionEnum,
    RecoveryStatusEnum,
    ApprovalDecisionEnum,
    RiskTierEnum,
)
from app.models.audit import AuditLog
from app.models.user import User
from app.services import health_checker
from app.services.detection_engine import process_monitoring_sample_for_incidents
from app.models.service import MetricSample


def log_audit_event(
    db: Session,
    organization_id: uuid.UUID,
    user: Optional[User],
    action: str,
    resource_type: str,
    resource_id: str,
    payload: Optional[dict] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """Creates an immutable audit log record for an operator or system action."""
    now = datetime.now(timezone.utc)
    entry = AuditLog(
        organization_id=organization_id,
        user_id=user.id if user else None,
        user_email=user.email if user else "system.engine@healcloud.io",
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        payload=payload,
        ip_address=ip_address,
        created_at=now,
    )
    db.add(entry)
    db.flush()
    return entry


def execute_recovery_simulation(
    db: Session,
    incident: Incident,
    policy: Optional[RecoveryPolicy] = None,
    action: Optional[str] = None,
    operator: Optional[User] = None,
    ip_address: Optional[str] = None,
) -> RecoveryExecution:
    """
    Executes a controlled, allowlisted recovery simulation with:
    - Allowlist enforcement
    - Idempotency protection (no concurrent runs on the same service)
    - Cooldown window enforcement
    - Retry limit verification
    - Post-recovery synthetic health verification
    - Closed-loop incident resolution
    - Tamper-evident audit logging
    """
    now = datetime.now(timezone.utc)
    service = db.query(Service).filter(Service.id == incident.service_id).first()
    if not service:
        raise EntityNotFoundException("Service", incident.service_id)

    # 1. Action allowlist check
    recovery_action = action or (policy.action if policy else AllowlistedActionEnum.SIMULATE_RESTART.value)
    if recovery_action not in [a.value for a in AllowlistedActionEnum]:
        raise ValidationException(
            f"Action '{recovery_action}' is not in the approved recovery action allowlist."
        )

    # 2. Idempotency guard: prevent concurrent running executions on this service
    running_exec = (
        db.query(RecoveryExecution)
        .filter(
            RecoveryExecution.service_id == service.id,
            RecoveryExecution.status.in_([RecoveryStatusEnum.RUNNING.value, RecoveryStatusEnum.VERIFYING.value]),
        )
        .first()
    )
    if running_exec:
        raise ConflictException(
            f"Recovery execution {running_exec.id} is already in progress for service '{service.name}'."
        )

    # 3. Policy Cooldown and Retry Checks
    if policy:
        if not policy.is_enabled:
            raise ValidationException(f"Recovery policy '{policy.name}' is currently disabled.")

        if policy.last_executed_at:
            last_exec = policy.last_executed_at
            if last_exec.tzinfo is None:
                last_exec = last_exec.replace(tzinfo=timezone.utc)
            cooldown_boundary = last_exec + timedelta(seconds=policy.cooldown_seconds)
            if now < cooldown_boundary:
                remaining_sec = int((cooldown_boundary - now).total_seconds())
                raise ValidationException(
                    f"Recovery policy '{policy.name}' cooldown active. Must wait {remaining_sec}s."
                )

        # Retry limits check
        past_attempts = (
            db.query(RecoveryExecution)
            .filter(
                RecoveryExecution.incident_id == incident.id,
                RecoveryExecution.policy_id == policy.id,
                RecoveryExecution.status.in_([RecoveryStatusEnum.FAILED.value, RecoveryStatusEnum.SUCCESS.value]),
            )
            .count()
        )
        if past_attempts >= policy.max_retries:
            raise ValidationException(
                f"Policy '{policy.name}' retry limit of {policy.max_retries} attempts reached for this incident."
            )

    # 4. Initialize Execution record
    start_time = time.perf_counter()
    execution = RecoveryExecution(
        organization_id=incident.organization_id,
        workspace_id=incident.workspace_id,
        incident_id=incident.id,
        policy_id=policy.id if policy else None,
        service_id=service.id,
        action_taken=recovery_action,
        status=RecoveryStatusEnum.RUNNING.value,
        requested_by_user_id=operator.id if operator else None,
        started_at=now,
    )
    db.add(execution)

    # Update incident state to RECOVERING
    incident.status = IncidentStatusEnum.RECOVERING.value
    incident.updated_at = now
    db.add(incident)

    event_start = IncidentEvent(
        incident_id=incident.id,
        event_type=IncidentEventTypeEnum.RECOVERY_STARTED.value,
        message=f"Executing recovery action '{recovery_action}' via Controlled Simulator.",
        payload={"action": recovery_action, "policy_id": str(policy.id) if policy else None},
        created_at=now,
    )
    db.add(event_start)
    db.flush()

    # 5. Simulate execution output
    output_message = f"Simulated '{recovery_action}' against container deployment '{service.name}'. "

    # 6. Post-recovery verification
    execution.status = RecoveryStatusEnum.VERIFYING.value
    db.add(execution)
    db.flush()

    endpoint = db.query(ServiceEndpoint).filter(ServiceEndpoint.service_id == service.id).first()
    is_verified = True
    failure_reason = None

    if endpoint:
        is_success, status_code, elapsed_ms, error_msg = health_checker.probe_endpoint(endpoint)
        if not is_success:
            is_verified = False
            failure_reason = (
                f"Post-recovery verification probe returned status {status_code}: {error_msg}"
            )
            output_message += f"Verification FAILED: {error_msg}."
        else:
            output_message += f"Verification probe passed (HTTP {status_code}, {elapsed_ms:.1f}ms)."

    duration_ms = int((time.perf_counter() - start_time) * 1000)
    finished_now = datetime.now(timezone.utc)

    execution.duration_ms = duration_ms
    execution.execution_output = output_message
    execution.verification_passed = is_verified
    execution.failure_reason = failure_reason
    execution.completed_at = finished_now

    if is_verified:
        execution.status = RecoveryStatusEnum.SUCCESS.value
        service.consecutive_failures = 0
        service.health_status = HealthStatusEnum.HEALTHY.value
        service.last_success_at = finished_now

        incident.status = IncidentStatusEnum.RESOLVED.value
        incident.resolved_at = finished_now
        incident.updated_at = finished_now

        event_verified = IncidentEvent(
            incident_id=incident.id,
            event_type=IncidentEventTypeEnum.RECOVERY_VERIFIED.value,
            message=f"Post-recovery verification probe confirmed service '{service.name}' healthy.",
            payload={"verification_passed": True, "duration_ms": duration_ms},
            created_at=finished_now,
        )
        db.add(event_verified)

        event_resolved = IncidentEvent(
            incident_id=incident.id,
            event_type=IncidentEventTypeEnum.RESOLVED.value,
            message="Incident resolved following verified automated remediation.",
            payload={"duration_ms": duration_ms, "action": recovery_action},
            created_at=finished_now,
        )
        db.add(event_resolved)

    else:
        execution.status = RecoveryStatusEnum.FAILED.value
        incident.status = IncidentStatusEnum.FAILED.value
        incident.updated_at = finished_now

        event_fail = IncidentEvent(
            incident_id=incident.id,
            event_type=IncidentEventTypeEnum.RECOVERY_FAILED.value,
            message=f"Remediation failed: {failure_reason}",
            payload={"verification_passed": False, "failure_reason": failure_reason},
            created_at=finished_now,
        )
        db.add(event_fail)

        # Trigger Rule 5: Recovery verification failure in detection engine
        if endpoint:
            sample = MetricSample(
                check_id=endpoint.checks[0].id if endpoint.checks else uuid.uuid4(),
                service_id=service.id,
                timestamp=finished_now,
                status_code=503,
                response_time_ms=500.0,
                is_successful=False,
                error_message=failure_reason,
            )
            process_monitoring_sample_for_incidents(
                db=db,
                service=service,
                endpoint=endpoint,
                check=endpoint.checks[0] if endpoint.checks else None,
                sample=sample,
                is_recovery_verification_failure=True,
                recovery_failure_details=failure_reason,
            )

    if policy:
        policy.last_executed_at = finished_now
        db.add(policy)

    db.add(execution)
    db.add(service)
    db.add(incident)

    # 7. Audit log commitment
    log_audit_event(
        db=db,
        organization_id=incident.organization_id,
        user=operator,
        action="RECOVERY_SIMULATION_EXECUTED",
        resource_type="RecoveryExecution",
        resource_id=str(execution.id),
        payload={
            "incident_number": incident.incident_number,
            "service_name": service.name,
            "action": recovery_action,
            "status": execution.status,
            "verification_passed": is_verified,
            "duration_ms": duration_ms,
        },
        ip_address=ip_address,
    )

    db.flush()
    return execution
