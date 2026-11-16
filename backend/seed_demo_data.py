"""
HealCloud Local Development & Demo Seeder
Populates the local SQLite database with realistic enterprise cloud reliability data.
"""

import sys
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.models.user import User
from app.models.organization import Organization, Workspace
from app.models.membership import Membership, RoleEnum
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
from app.core.security import get_password_hash


def seed():
    print("=" * 60)
    print("Seeding HealCloud Local Development Database...")
    print("=" * 60)

    db: Session = SessionLocal()
    try:
        # Check if already seeded
        existing_user = db.query(User).filter(User.email == "admin@healcloud.io").first()
        if existing_user:
            print("Database already contains demo user 'admin@healcloud.io'.")
            print("Resetting demo tenant data...")
            # Delete in cascade
            org = db.query(Organization).filter(Organization.slug == "acme-cloud").first()
            if org:
                db.delete(org)
            db.delete(existing_user)
            db.commit()

        now = datetime.now(timezone.utc)

        # 1. Primary Demo User
        user = User(
            id=uuid.uuid4(),
            email="admin@healcloud.io",
            full_name="Alex Vance (Lead SRE)",
            password_hash=get_password_hash("Password123!"),
            is_active=True,
            is_platform_admin=True,
        )
        db.add(user)

        # 2. Organization & Workspaces
        org = Organization(
            id=uuid.uuid4(),
            name="Acme Cloud Corp",
            slug="acme-cloud",
            is_active=True,
        )
        db.add(org)

        prod_ws = Workspace(
            id=uuid.uuid4(),
            organization_id=org.id,
            name="production",
            slug="prod",
            description="Primary Production Microservices Fleet & Autonomous Healing",
        )
        db.add(prod_ws)

        staging_ws = Workspace(
            id=uuid.uuid4(),
            organization_id=org.id,
            name="staging",
            slug="stage",
            description="Pre-production Validation & Chaos Engineering Cluster",
        )
        db.add(staging_ws)

        # 3. Membership
        membership = Membership(
            id=uuid.uuid4(),
            organization_id=org.id,
            user_id=user.id,
            role=RoleEnum.ORG_OWNER.value,
        )
        db.add(membership)

        # 4. Monitored Microservices in Production
        services_data = [
            {
                "name": "payment-gateway",
                "desc": "Stripe & PCI-DSS transaction processing engine",
                "health": HealthStatusEnum.HEALTHY.value,
                "failures": 0,
                "url": "https://httpbin.org/status/200",
                "timeout": 3000,
                "interval": 30,
                "base_latency": 45.0,
            },
            {
                "name": "auth-service",
                "desc": "OAuth2 / OIDC token issuance and user identity service",
                "health": HealthStatusEnum.HEALTHY.value,
                "failures": 0,
                "url": "https://httpbin.org/status/200",
                "timeout": 1500,
                "interval": 30,
                "base_latency": 28.0,
            },
            {
                "name": "order-processing-api",
                "desc": "Order ingestion and dispatch pipeline",
                "health": HealthStatusEnum.DEGRADED.value,
                "failures": 3,
                "url": "https://httpbin.org/status/503",
                "timeout": 2000,
                "interval": 15,
                "base_latency": 180.0,
            },
            {
                "name": "inventory-sync",
                "desc": "Distributed warehouse and catalog inventory reconciliation",
                "health": HealthStatusEnum.HEALTHY.value,
                "failures": 0,
                "url": "https://httpbin.org/status/200",
                "timeout": 4000,
                "interval": 60,
                "base_latency": 55.0,
            },
        ]

        created_services = {}

        for s_def in services_data:
            svc = Service(
                id=uuid.uuid4(),
                organization_id=org.id,
                workspace_id=prod_ws.id,
                name=s_def["name"],
                description=s_def["desc"],
                health_status=s_def["health"],
                consecutive_failures=s_def["failures"],
                last_success_at=now - timedelta(seconds=12) if s_def["failures"] == 0 else now - timedelta(minutes=15),
                last_failure_at=now - timedelta(seconds=15) if s_def["failures"] > 0 else None,
            )
            db.add(svc)
            created_services[s_def["name"]] = svc

            ep = ServiceEndpoint(
                id=uuid.uuid4(),
                service_id=svc.id,
                url=s_def["url"],
                method="GET",
                expected_status_code=200,
                timeout_ms=s_def["timeout"],
            )
            db.add(ep)

            check = MonitoringCheck(
                id=uuid.uuid4(),
                service_id=svc.id,
                endpoint_id=ep.id,
                interval_seconds=s_def["interval"],
                consecutive_failure_threshold=3,
                is_enabled=True,
                last_checked_at=now - timedelta(seconds=10),
            )
            db.add(check)

            # Generate realistic telemetry samples
            for i in range(12):
                sample_time = now - timedelta(minutes=(12 - i) * 3)
                if s_def["failures"] > 0 and i >= 9:
                    # Recent failures on degraded service
                    sample = MetricSample(
                        id=uuid.uuid4(),
                        check_id=check.id,
                        service_id=svc.id,
                        timestamp=sample_time,
                        status_code=503,
                        response_time_ms=750.0 + (i * 40),
                        is_successful=False,
                        error_message="HTTP 503: Service Unavailable",
                    )
                else:
                    sample = MetricSample(
                        id=uuid.uuid4(),
                        check_id=check.id,
                        service_id=svc.id,
                        timestamp=sample_time,
                        status_code=200,
                        response_time_ms=s_def["base_latency"] + (i * 2.5),
                        is_successful=True,
                        error_message=None,
                    )
                db.add(sample)

        # 5. Recovery Policies
        policy_restart = RecoveryPolicy(
            id=uuid.uuid4(),
            organization_id=org.id,
            workspace_id=prod_ws.id,
            service_id=created_services["order-processing-api"].id,
            name="Auto-Remediate Transient Container Outage",
            trigger_condition="CONSECUTIVE_FAILURES",
            action=AllowlistedActionEnum.SIMULATE_RESTART.value,
            requires_approval=True,
            max_retries=3,
            cooldown_seconds=300,
            timeout_seconds=60,
            is_enabled=True,
        )
        db.add(policy_restart)

        policy_scale = RecoveryPolicy(
            id=uuid.uuid4(),
            organization_id=org.id,
            workspace_id=prod_ws.id,
            service_id=created_services["payment-gateway"].id,
            name="High Latency Scale-Out Mitigation",
            trigger_condition="RESPONSE_TIME_EXCEEDED",
            action=AllowlistedActionEnum.SIMULATE_SCALE_UP.value,
            requires_approval=False,
            max_retries=2,
            cooldown_seconds=600,
            timeout_seconds=120,
            is_enabled=True,
        )
        db.add(policy_scale)

        policy_circuit = RecoveryPolicy(
            id=uuid.uuid4(),
            organization_id=org.id,
            workspace_id=prod_ws.id,
            service_id=created_services["auth-service"].id,
            name="Database Connection Pool Circuit Breaker",
            trigger_condition="SERVICE_UNAVAILABLE",
            action=AllowlistedActionEnum.SIMULATE_CIRCUIT_BREAK.value,
            requires_approval=True,
            max_retries=1,
            cooldown_seconds=300,
            timeout_seconds=45,
            is_enabled=True,
        )
        db.add(policy_circuit)

        # 6. Active Incident on order-processing-api
        incident = Incident(
            id=uuid.uuid4(),
            organization_id=org.id,
            workspace_id=prod_ws.id,
            service_id=created_services["order-processing-api"].id,
            incident_number="INC-2026-0001",
            title="Service Degradation: order-processing-api consecutive HTTP 503 errors",
            description="Repeated synthetic probe failures detected by HealCloud monitoring engine. Upstream container unresponsive to health probes.",
            severity=IncidentSeverityEnum.P1_CRITICAL.value,
            status=IncidentStatusEnum.INVESTIGATING.value,
            assigned_to_user_id=user.id,
            detected_at=now - timedelta(minutes=15),
            acknowledged_at=now - timedelta(minutes=12),
        )
        db.add(incident)

        # Incident Events (Timeline)
        db.add(IncidentEvent(
            id=uuid.uuid4(),
            incident_id=incident.id,
            event_type=IncidentEventTypeEnum.DETECTED.value,
            message="Incident INC-2026-0001 automatically triggered due to 3 consecutive synthetic check failures.",
            payload={"consecutive_failures": 3, "status_code": 503},
            created_at=now - timedelta(minutes=15),
        ))
        db.add(IncidentEvent(
            id=uuid.uuid4(),
            incident_id=incident.id,
            event_type=IncidentEventTypeEnum.DIAGNOSED.value,
            message="Deterministic RCA engine identified upstream container failure with 94% confidence.",
            payload={"rule": "RepeatedSyntheticProbeFailuresRule", "confidence": 0.94},
            created_at=now - timedelta(minutes=14),
        ))
        db.add(IncidentEvent(
            id=uuid.uuid4(),
            incident_id=incident.id,
            event_type=IncidentEventTypeEnum.ACKNOWLEDGED.value,
            message=f"Incident acknowledged by Lead SRE {user.full_name}.",
            payload={"user_id": str(user.id)},
            created_at=now - timedelta(minutes=12),
        ))
        db.add(IncidentEvent(
            id=uuid.uuid4(),
            incident_id=incident.id,
            event_type=IncidentEventTypeEnum.RECOVERY_REQUESTED.value,
            message="Matched policy 'Auto-Remediate Transient Container Outage'. Queued Human-in-the-Loop dual-custody approval request.",
            payload={"action": "SIMULATE_RESTART", "requires_approval": True},
            created_at=now - timedelta(minutes=10),
        ))

        # Explainable Diagnosis
        diagnosis = Diagnosis(
            id=uuid.uuid4(),
            incident_id=incident.id,
            rule_name="RepeatedSyntheticProbeFailuresRule",
            root_cause_hypothesis="Synthetic health probe returned HTTP 503 Service Unavailable (3 consecutive failures). Upstream container unresponsive.",
            confidence_score=0.94,
            evidence={
                "target_url": "https://httpbin.org/status/503",
                "status_code": 503,
                "consecutive_failures": 3,
                "threshold": 3,
                "probe_latencies_ms": [820.5, 890.1, 940.4],
            },
            recommended_action=AllowlistedActionEnum.SIMULATE_RESTART.value,
            created_at=now - timedelta(minutes=14),
        )
        db.add(diagnosis)

        # 7. Pending Approval Request in Approvals Inbox
        approval = ApprovalRequest(
            id=uuid.uuid4(),
            organization_id=org.id,
            workspace_id=prod_ws.id,
            incident_id=incident.id,
            service_id=created_services["order-processing-api"].id,
            proposed_action=AllowlistedActionEnum.SIMULATE_RESTART.value,
            risk_tier=RiskTierEnum.TIER_2_MEDIUM.value,
            blast_radius="Isolated container deployment restart in production namespace",
            status=ApprovalDecisionEnum.PENDING.value,
            requested_by_user_id=None,  # Autonomous System
            requested_at=now - timedelta(minutes=10),
        )
        db.add(approval)

        # 8. Historical Successful Recovery on auth-service
        prev_incident = Incident(
            id=uuid.uuid4(),
            organization_id=org.id,
            workspace_id=prod_ws.id,
            service_id=created_services["auth-service"].id,
            incident_number="INC-2026-0000",
            title="Resolved: auth-service memory pressure threshold spike",
            description="High latency threshold violation automatically recovered via container restart.",
            severity=IncidentSeverityEnum.P2_HIGH.value,
            status=IncidentStatusEnum.RESOLVED.value,
            assigned_to_user_id=user.id,
            detected_at=now - timedelta(hours=2),
            acknowledged_at=now - timedelta(hours=2, minutes=-2),
            resolved_at=now - timedelta(hours=1, minutes=55),
        )
        db.add(prev_incident)

        past_exec = RecoveryExecution(
            id=uuid.uuid4(),
            organization_id=org.id,
            workspace_id=prod_ws.id,
            incident_id=prev_incident.id,
            policy_id=policy_restart.id,
            service_id=created_services["auth-service"].id,
            action_taken=AllowlistedActionEnum.SIMULATE_RESTART.value,
            status=RecoveryStatusEnum.SUCCESS.value,
            execution_output="Simulated 'SIMULATE_RESTART' against container deployment 'auth-service'. Container gracefully stopped, recreated, and started. Verification probe passed: 200 OK (28.4ms latency).",
            duration_ms=1420,
            verification_passed=True,
            requested_by_user_id=user.id,
            started_at=now - timedelta(hours=1, minutes=58),
            completed_at=now - timedelta(hours=1, minutes=55),
        )
        db.add(past_exec)

        # 9. Audit Logs
        audit_events = [
            ("USER_REGISTERED", "User", str(user.id), {"email": user.email, "role": "ORG_OWNER"}),
            ("ORGANIZATION_CREATED", "Organization", str(org.id), {"name": org.name, "slug": org.slug}),
            ("SERVICE_REGISTERED", "Service", str(created_services["order-processing-api"].id), {"name": "order-processing-api"}),
            ("RECOVERY_POLICY_CREATED", "RecoveryPolicy", str(policy_restart.id), {"name": policy_restart.name, "action": policy_restart.action}),
            ("INCIDENT_DETECTED", "Incident", str(incident.id), {"incident_number": incident.incident_number, "severity": incident.severity}),
            ("APPROVAL_REQUEST_QUEUED", "ApprovalRequest", str(approval.id), {"action": approval.proposed_action, "tier": approval.risk_tier}),
        ]

        for action, r_type, r_id, payload in audit_events:
            db.add(AuditLog(
                id=uuid.uuid4(),
                organization_id=org.id,
                user_id=user.id,
                user_email=user.email,
                action=action,
                resource_type=r_type,
                resource_id=r_id,
                payload=payload,
                ip_address="127.0.0.1",
                created_at=now - timedelta(minutes=15),
            ))

        db.commit()
        print("Successfully seeded HealCloud database!")
        print(f"Organization:  {org.name} (Slug: {org.slug})")
        print(f"Workspace:     {prod_ws.name} (Slug: {prod_ws.slug})")
        print(f"Demo Account:  admin@healcloud.io")
        print(f"Password:      Password123!")
        print(f"Services:      {len(services_data)} microservices registered")
        print(f"Active Incident: {incident.incident_number} ({incident.title})")
        print(f"Pending Approvals: 1 in HITL inbox")
        print("=" * 60)

    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()

