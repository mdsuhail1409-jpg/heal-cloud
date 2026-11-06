"""
HealCloud Incident Detection and Rule-Based Explainable Diagnosis Engine
"""

import uuid
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.service import (
    Service,
    ServiceEndpoint,
    MonitoringCheck,
    MetricSample,
    HealthStatusEnum,
)
from app.models.incident import (
    Incident,
    IncidentEvent,
    Diagnosis,
    IncidentSeverityEnum,
    IncidentStatusEnum,
    IncidentEventTypeEnum,
)
from app.core.exceptions import HealCloudException, EntityNotFoundException, ValidationException


ACTIVE_INCIDENT_STATUSES = [
    IncidentStatusEnum.OPEN.value,
    IncidentStatusEnum.ACKNOWLEDGED.value,
    IncidentStatusEnum.INVESTIGATING.value,
    IncidentStatusEnum.RECOVERY_PENDING.value,
    IncidentStatusEnum.RECOVERING.value,
]

SEVERITY_ORDER = {
    IncidentSeverityEnum.P4_LOW.value: 1,
    IncidentSeverityEnum.P3_MEDIUM.value: 2,
    IncidentSeverityEnum.P2_HIGH.value: 3,
    IncidentSeverityEnum.P1_CRITICAL.value: 4,
}


def generate_incident_number(db: Session) -> str:
    """Generates an enterprise-formatted incident identifier: INC-YYYY-NNNN."""
    year = datetime.now(timezone.utc).year
    prefix = f"INC-{year}-"
    count = db.query(Incident).filter(Incident.incident_number.like(f"{prefix}%")).count()
    candidate = f"{prefix}{count + 1:04d}"

    # Ensure uniqueness in case of race conditions
    while db.query(Incident).filter(Incident.incident_number == candidate).first():
        candidate = f"{prefix}{uuid.uuid4().hex[:6].upper()}"

    return candidate


def find_active_incident(
    db: Session,
    workspace_id: uuid.UUID,
    service_id: uuid.UUID,
) -> Optional[Incident]:
    """Retrieves an existing active incident for a service within a workspace."""
    return (
        db.query(Incident)
        .filter(
            Incident.workspace_id == workspace_id,
            Incident.service_id == service_id,
            Incident.status.in_(ACTIVE_INCIDENT_STATUSES),
        )
        .order_by(desc(Incident.detected_at))
        .first()
    )


class RuleEvaluationResult:
    def __init__(
        self,
        triggered: bool,
        rule_name: str,
        title: str,
        severity: IncidentSeverityEnum,
        hypothesis: str,
        confidence_score: float,
        evidence: Dict[str, Any],
        recommended_action: str,
    ):
        self.triggered = triggered
        self.rule_name = rule_name
        self.title = title
        self.severity = severity
        self.hypothesis = hypothesis
        self.confidence_score = confidence_score
        self.evidence = evidence
        self.recommended_action = recommended_action


def evaluate_detection_rules(
    service: Service,
    endpoint: Optional[ServiceEndpoint],
    check: Optional[MonitoringCheck],
    sample: MetricSample,
    is_recovery_verification_failure: bool = False,
    recovery_failure_details: Optional[str] = None,
) -> Optional[RuleEvaluationResult]:
    """
    Evaluates monitoring telemetry and failure states against the 5 approved threshold rules:
    1. Recovery verification failure
    2. Excessive consecutive failures (>= 5)
    3. Service unavailable (status_code is None or >= 500)
    4. Repeated health-check failure (consecutive_failures >= threshold)
    5. Response-time threshold exceeded (> 80% timeout or SLA threshold)
    """
    consecutive_failures = service.consecutive_failures
    status_code = sample.status_code
    response_time_ms = sample.response_time_ms
    error_message = sample.error_message
    threshold = check.consecutive_failure_threshold if check else 3
    timeout_ms = endpoint.timeout_ms if endpoint else 5000

    # Rule 5: Recovery verification failure
    if is_recovery_verification_failure:
        return RuleEvaluationResult(
            triggered=True,
            rule_name="RULE_RECOVERY_VERIFICATION_FAILURE",
            title=f"Recovery Verification Failed: Remediation failed to restore {service.name}",
            severity=IncidentSeverityEnum.P1_CRITICAL,
            hypothesis=(
                f"Automated recovery execution finished, but post-recovery health verification "
                f"probe failed. Target service '{service.name}' remains non-operational."
            ),
            confidence_score=0.92,
            evidence={
                "trigger": "recovery_verification_failure",
                "details": recovery_failure_details or error_message or "Probe returned non-2xx post remediation.",
                "status_code": status_code,
                "response_time_ms": response_time_ms,
            },
            recommended_action="MANUAL_INVESTIGATION",
        )

    # Rule 4: Excessive consecutive failures
    if consecutive_failures >= 5:
        return RuleEvaluationResult(
            triggered=True,
            rule_name="RULE_EXCESSIVE_CONSECUTIVE_FAILURES",
            title=f"Critical Outage: {service.name} reached {consecutive_failures} consecutive failures",
            severity=IncidentSeverityEnum.P1_CRITICAL,
            hypothesis=(
                f"Service '{service.name}' has accumulated {consecutive_failures} sustained consecutive "
                f"probe failures. The service is experiencing a persistent outage."
            ),
            confidence_score=0.95,
            evidence={
                "trigger": "excessive_consecutive_failures",
                "consecutive_failures": consecutive_failures,
                "critical_threshold": 5,
                "health_status": service.health_status,
                "last_error": error_message,
                "last_status_code": status_code,
            },
            recommended_action="SIMULATE_RESTART",
        )

    # Rule 1: Service unavailable (status_code is None or 5xx)
    if not sample.is_successful and (status_code is None or status_code >= 500):
        is_503 = status_code == 503
        severity = IncidentSeverityEnum.P1_CRITICAL if (status_code is None or is_503) else IncidentSeverityEnum.P2_HIGH
        return RuleEvaluationResult(
            triggered=True,
            rule_name="RULE_SERVICE_UNAVAILABLE",
            title=f"Service Unavailable: {service.name} unreachable or HTTP {status_code or 'ERR'}",
            severity=severity,
            hypothesis=(
                f"Target endpoint '{endpoint.url if endpoint else service.name}' is unreachable or returning "
                f"server errors (HTTP {status_code or 'Connection Error'}). Process crash or port unresponsiveness likely."
            ),
            confidence_score=0.90 if status_code is None else 0.85,
            evidence={
                "trigger": "service_unavailable",
                "status_code": status_code,
                "expected_status_code": endpoint.expected_status_code if endpoint else 200,
                "response_time_ms": response_time_ms,
                "error_message": error_message,
                "consecutive_failures": consecutive_failures,
            },
            recommended_action="SIMULATE_RESTART",
        )

    # Rule 2: Repeated health-check failure
    if not sample.is_successful and consecutive_failures >= threshold:
        return RuleEvaluationResult(
            triggered=True,
            rule_name="RULE_REPEATED_HEALTH_CHECK_FAILURE",
            title=f"Repeated Health Check Failure: {service.name} failed {consecutive_failures} consecutive checks",
            severity=IncidentSeverityEnum.P2_HIGH,
            hypothesis=(
                f"Service '{service.name}' has failed {consecutive_failures} consecutive checks, "
                f"crossing the configured threshold of {threshold}. Degradation is reproducible."
            ),
            confidence_score=0.88,
            evidence={
                "trigger": "repeated_health_check_failure",
                "consecutive_failures": consecutive_failures,
                "failure_threshold": threshold,
                "last_status_code": status_code,
                "error_message": error_message,
            },
            recommended_action="SIMULATE_RESTART",
        )

    # Rule 3: Response-time threshold exceeded (Latency degradation)
    # Trigger when response time exceeds 80% of configured timeout or > 1500ms
    latency_threshold = max(timeout_ms * 0.8, 1500.0)
    if response_time_ms > latency_threshold:
        return RuleEvaluationResult(
            triggered=True,
            rule_name="RULE_RESPONSE_TIME_EXCEEDED",
            title=f"Latency Degraded: {service.name} response time {response_time_ms:.1f}ms exceeds {latency_threshold:.1f}ms",
            severity=IncidentSeverityEnum.P3_MEDIUM,
            hypothesis=(
                f"Response latency ({response_time_ms:.1f}ms) exceeded SLA threshold ({latency_threshold:.1f}ms). "
                f"Indicates thread starvation, high concurrency, or unoptimized database queries."
            ),
            confidence_score=0.80,
            evidence={
                "trigger": "response_time_threshold_exceeded",
                "measured_response_time_ms": response_time_ms,
                "latency_threshold_ms": latency_threshold,
                "status_code": status_code,
            },
            recommended_action="SIMULATE_SCALE_UP",
        )

    return None


def process_monitoring_sample_for_incidents(
    db: Session,
    service: Service,
    endpoint: Optional[ServiceEndpoint],
    check: Optional[MonitoringCheck],
    sample: MetricSample,
    is_recovery_verification_failure: bool = False,
    recovery_failure_details: Optional[str] = None,
) -> Tuple[Optional[Incident], bool]:
    """
    Ingests a MetricSample, evaluates detection rules, performs duplicate prevention,
    or handles auto-resolution if the service has recovered.

    Returns:
    (incident, is_new_incident)
    """
    now = datetime.now(timezone.utc)
    active_inc = find_active_incident(db, service.workspace_id, service.id)

    # 1. Evaluate detection rules first
    rule_match = evaluate_detection_rules(
        service=service,
        endpoint=endpoint,
        check=check,
        sample=sample,
        is_recovery_verification_failure=is_recovery_verification_failure,
        recovery_failure_details=recovery_failure_details,
    )

    # 2. If no rule matched, check if service has recovered to healthy state
    if not rule_match:
        if sample.is_successful and service.health_status == HealthStatusEnum.HEALTHY.value and service.consecutive_failures == 0:
            if active_inc:
                active_inc.status = IncidentStatusEnum.RESOLVED.value
                active_inc.resolved_at = now
                active_inc.updated_at = now

                event = IncidentEvent(
                    incident_id=active_inc.id,
                    event_type=IncidentEventTypeEnum.RESOLVED.value,
                    message=(
                        f"Service '{service.name}' restored to healthy operation with response time "
                        f"{sample.response_time_ms:.1f}ms. Incident marked as RESOLVED."
                    ),
                    payload={
                        "status_code": sample.status_code,
                        "response_time_ms": sample.response_time_ms,
                        "consecutive_failures": 0,
                    },
                    created_at=now,
                )
                db.add(event)
                db.add(active_inc)
                db.flush()
                return active_inc, False
        return None, False

    # 3. Duplicate Incident Prevention
    if active_inc:
        # Escalate severity if new rule match is higher severity
        existing_rank = SEVERITY_ORDER.get(active_inc.severity, 0)
        new_rank = SEVERITY_ORDER.get(rule_match.severity.value, 0)
        if new_rank > existing_rank:
            active_inc.severity = rule_match.severity.value
            active_inc.title = rule_match.title

        active_inc.updated_at = now

        # Append threshold breach event to existing incident timeline
        event = IncidentEvent(
            incident_id=active_inc.id,
            event_type=IncidentEventTypeEnum.THRESHOLD_BREACHED.value,
            message=(
                f"Threshold re-breached under rule {rule_match.rule_name}. "
                f"Duplicate incident prevented; timeline updated."
            ),
            payload=rule_match.evidence,
            created_at=now,
        )
        db.add(event)

        # Record latest diagnosis
        diagnosis = Diagnosis(
            incident_id=active_inc.id,
            rule_name=rule_match.rule_name,
            root_cause_hypothesis=rule_match.hypothesis,
            confidence_score=rule_match.confidence_score,
            evidence=rule_match.evidence,
            recommended_action=rule_match.recommended_action,
            created_at=now,
        )
        db.add(diagnosis)
        db.add(active_inc)
        db.flush()
        return active_inc, False

    # 4. Create New Incident
    incident_number = generate_incident_number(db)
    new_inc = Incident(
        organization_id=service.organization_id,
        workspace_id=service.workspace_id,
        service_id=service.id,
        incident_number=incident_number,
        title=rule_match.title,
        description=f"Automated incident triggered by {rule_match.rule_name}.",
        severity=rule_match.severity.value,
        status=IncidentStatusEnum.OPEN.value,
        detected_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(new_inc)
    db.flush()

    # Add DETECTED event
    detect_event = IncidentEvent(
        incident_id=new_inc.id,
        event_type=IncidentEventTypeEnum.DETECTED.value,
        message=f"Incident detected by rule {rule_match.rule_name}: {rule_match.title}",
        payload=rule_match.evidence,
        created_at=now,
    )
    db.add(detect_event)

    # Add initial Diagnosis
    diagnosis = Diagnosis(
        incident_id=new_inc.id,
        rule_name=rule_match.rule_name,
        root_cause_hypothesis=rule_match.hypothesis,
        confidence_score=rule_match.confidence_score,
        evidence=rule_match.evidence,
        recommended_action=rule_match.recommended_action,
        created_at=now,
    )
    db.add(diagnosis)

    # Add DIAGNOSED event
    diag_event = IncidentEvent(
        incident_id=new_inc.id,
        event_type=IncidentEventTypeEnum.DIAGNOSED.value,
        message=(
            f"Rule-based diagnosis completed: {rule_match.hypothesis} "
            f"(Confidence: {rule_match.confidence_score*100:.0f}%, Recommended: {rule_match.recommended_action})"
        ),
        payload={
            "rule": rule_match.rule_name,
            "confidence": rule_match.confidence_score,
            "recommended_action": rule_match.recommended_action,
        },
        created_at=now,
    )
    db.add(diag_event)
    db.flush()

    return new_inc, True


def run_explainable_diagnosis(
    db: Session,
    incident_id: uuid.UUID,
    force_re_evaluation: bool = False,
) -> Diagnosis:
    """
    Executes an on-demand, explainable root-cause diagnosis for an existing incident.
    Inspects recent metric samples and failure evidence.
    Strictly avoids inventing a root cause if evidence is insufficient.
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise EntityNotFoundException("Incident", incident_id)

    service = db.query(Service).filter(Service.id == incident.service_id).first()
    if not service:
        raise EntityNotFoundException("Service", incident.service_id)

    # Fetch latest 10 metric samples for evidence correlation
    recent_samples = (
        db.query(MetricSample)
        .filter(MetricSample.service_id == service.id)
        .order_by(desc(MetricSample.timestamp))
        .limit(10)
        .all()
    )

    now = datetime.now(timezone.utc)

    # If recent samples exist, evaluate against rules
    if recent_samples:
        latest = recent_samples[0]
        # Find endpoint and check
        check = db.query(MonitoringCheck).filter(MonitoringCheck.id == latest.check_id).first()
        endpoint = db.query(ServiceEndpoint).filter(ServiceEndpoint.service_id == service.id).first()

        match = evaluate_detection_rules(service, endpoint, check, latest)
        if match:
            diag = Diagnosis(
                incident_id=incident.id,
                rule_name=match.rule_name,
                root_cause_hypothesis=match.hypothesis,
                confidence_score=match.confidence_score,
                evidence=match.evidence,
                recommended_action=match.recommended_action,
                created_at=now,
            )
            db.add(diag)
            event = IncidentEvent(
                incident_id=incident.id,
                event_type=IncidentEventTypeEnum.DIAGNOSED.value,
                message=f"Explainable diagnosis evaluated rule {match.rule_name}.",
                payload={"rule": match.rule_name, "recommended_action": match.recommended_action},
                created_at=now,
            )
            db.add(event)
            db.flush()
            return diag

    # When evidence is insufficient, do NOT invent a cause
    diag = Diagnosis(
        incident_id=incident.id,
        rule_name="RULE_INSUFFICIENT_EVIDENCE",
        root_cause_hypothesis=(
            "Insufficient telemetry evidence: recent metric samples show nominal latency and status codes, "
            "or insufficient failure samples exist to determine an unambiguous root cause."
        ),
        confidence_score=0.25,
        evidence={
            "recent_sample_count": len(recent_samples),
            "service_health": service.health_status,
            "consecutive_failures": service.consecutive_failures,
        },
        recommended_action="MANUAL_INVESTIGATION",
        created_at=now,
    )
    db.add(diag)
    event = IncidentEvent(
        incident_id=incident.id,
        event_type=IncidentEventTypeEnum.DIAGNOSED.value,
        message="Diagnosis executed: insufficient evidence to pinpoint root cause.",
        payload={"rule": "RULE_INSUFFICIENT_EVIDENCE", "recommended_action": "MANUAL_INVESTIGATION"},
        created_at=now,
    )
    db.add(event)
    db.flush()
    return diag
