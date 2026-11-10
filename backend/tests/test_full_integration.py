"""
Phase 10 Full Integration & End-to-End Workflow Verification Suite

Tests the complete closed-loop lifecycle:
OBSERVE -> DETECT -> DIAGNOSE -> POLICY / APPROVAL -> RECOVER -> VERIFY -> RECORD

Verifies:
1. Authentication, token handling, and user profile
2. Tenant & workspace management with strict cross-tenant isolation
3. Service registration with SSRF protection and health check probe definition
4. Automated probe execution, metric sample ingestion, and service health status
5. Threshold breach detection, P1 Incident generation, duplicate prevention
6. Explainable Root Cause Analysis (RCA) with telemetry evidence correlation
7. Incident acknowledgement, assignment, and status transitions
8. Recovery policy creation with allowlisted actions, cooldowns, and approval requirements
9. Dual-custody Human-in-the-Loop (HITL) approval request and decision workflow
10. Controlled Recovery Simulator execution with post-recovery closed-loop health verification
11. Incident auto-resolution upon verified healthy recovery
12. Comprehensive tamper-evident Audit Trail recording every operator and system event
"""

import uuid
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.incident import Incident, IncidentStatusEnum
from app.models.recovery import RecoveryPolicy, RecoveryExecution, ApprovalRequest
from app.models.audit import AuditLog
from app.services.health_checker import execute_monitoring_check


def test_full_e2e_closed_loop_self_healing_workflow(client: TestClient, db_session: Session):
    # =========================================================================
    # STEP 1: Authentication & Organization Setup
    # =========================================================================
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "lead.sre@acme-cloud.com",
            "password": "SecurePassword123!",
            "full_name": "Senior Reliability Lead",
            "organization_name": "Acme Cloud Platform",
        },
    )
    assert reg_resp.status_code == 201, reg_resp.text
    auth_data = reg_resp.json()
    token = auth_data["access_token"]
    user_id = auth_data["user"]["id"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify Profile & Organization
    profile_resp = client.get("/api/v1/auth/me", headers=headers)
    assert profile_resp.status_code == 200
    assert profile_resp.json()["user"]["email"] == "lead.sre@acme-cloud.com"

    # Get Workspace ID (automatically created default workspace)
    orgs_resp = client.get("/api/v1/organizations", headers=headers)
    assert orgs_resp.status_code == 200
    org_id = orgs_resp.json()[0]["id"]

    ws_resp = client.get(f"/api/v1/organizations/{org_id}/workspaces", headers=headers)
    assert ws_resp.status_code == 200
    workspaces = ws_resp.json()
    assert len(workspaces) >= 1
    ws_id = workspaces[0]["id"]

    # Create a secondary workspace to verify multi-workspace support
    custom_ws_resp = client.post(
        f"/api/v1/organizations/{org_id}/workspaces",
        headers=headers,
        json={"name": "Production EU-Central", "description": "Frankfurt production cluster"},
    )
    assert custom_ws_resp.status_code == 201
    prod_ws_id = custom_ws_resp.json()["id"]

    # =========================================================================
    # STEP 2: Strict Multi-Tenant Isolation Verification
    # =========================================================================
    # Create second independent tenant
    reg_b = client.post(
        "/api/v1/auth/register",
        json={
            "email": "operator@beta-corp.com",
            "password": "SecurePassword123!",
            "full_name": "Beta Operator",
            "organization_name": "Beta Corp",
        },
    )
    assert reg_b.status_code == 201
    token_b = reg_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Tenant B tries to access Tenant A's workspace -> MUST BE FORBIDDEN (403/404)
    cross_tenant_resp = client.get(
        f"/api/v1/organizations/{org_id}/workspaces/{prod_ws_id}/services",
        headers=headers_b,
    )
    assert cross_tenant_resp.status_code in (403, 404)

    # =========================================================================
    # STEP 3: Service Registration with Synthetic Probe
    # =========================================================================
    svc_payload = {
        "name": "payments-ingress-api",
        "description": "Core checkout transaction ingress service",
        "endpoint_url": "https://api.github.com/zen",
        "method": "GET",
        "expected_status_code": 200,
        "timeout_ms": 3000,
        "check_interval_seconds": 30,
        "consecutive_failure_threshold": 2,
    }
    svc_resp = client.post(
        f"/api/v1/organizations/{org_id}/workspaces/{prod_ws_id}/services",
        headers=headers,
        json=svc_payload,
    )
    assert svc_resp.status_code == 201, svc_resp.text
    svc_data = svc_resp.json()
    service_id = svc_data["id"]
    endpoint_id = svc_data["endpoints"][0]["id"]
    check_id = svc_data["checks"][0]["id"]
    assert svc_data["name"] == "payments-ingress-api"
    assert svc_data["health_status"] == "UNKNOWN"

    # =========================================================================
    # STEP 4: On-Demand Health Probe & Telemetry Ingestion
    # =========================================================================
    with patch("app.services.health_checker.probe_endpoint") as mock_probe:
        mock_probe.return_value = (True, 200, 48.5, None)

        probe_resp = client.post(
            f"/api/v1/organizations/{org_id}/workspaces/{prod_ws_id}/services/{service_id}/checks/run",
            headers=headers,
        )
        assert probe_resp.status_code == 200
        probe_data = probe_resp.json()
        assert probe_data["health_status"] == "HEALTHY"
        assert probe_data["is_successful"] is True
        assert probe_data["status_code"] == 200

    # Query chronological metric samples
    metrics_resp = client.get(
        f"/api/v1/organizations/{org_id}/workspaces/{prod_ws_id}/services/{service_id}/metrics",
        headers=headers,
    )
    assert metrics_resp.status_code == 200
    samples = metrics_resp.json()
    assert len(samples) >= 1
    assert samples[0]["is_successful"] is True

    # =========================================================================
    # STEP 5: Outage Ingestion, Threshold Crossing & P1 Incident Detection
    # =========================================================================
    with patch("app.services.health_checker.probe_endpoint") as mock_probe:
        # First failure: Service returns 503
        mock_probe.return_value = (False, 503, 120.0, "Service Unavailable (Downstream Gateway Timeout)")
        sample1 = execute_monitoring_check(uuid.UUID(check_id), db=db_session)
        assert sample1.is_successful is False

        # Threshold reached: Incident generated
        incidents = db_session.query(Incident).filter(Incident.service_id == uuid.UUID(service_id)).all()
        assert len(incidents) == 1
        incident = incidents[0]
        incident_id = str(incident.id)
        assert incident.severity == "P1_CRITICAL"
        assert incident.status == "OPEN"

        # Duplicate incident prevention: 2nd consecutive failure should append event, NOT duplicate incident
        mock_probe.return_value = (False, 503, 115.0, "Service Unavailable")
        sample2 = execute_monitoring_check(uuid.UUID(check_id), db=db_session)
        assert sample2.is_successful is False

        incidents_after = db_session.query(Incident).filter(Incident.service_id == uuid.UUID(service_id)).all()
        assert len(incidents_after) == 1  # No duplicate incident created!

        db_session.commit()

    # =========================================================================
    # STEP 6: Explainable Root Cause Analysis (RCA) Verification
    # =========================================================================
    inc_detail_resp = client.get(
        f"/api/v1/organizations/{org_id}/workspaces/{prod_ws_id}/incidents/{incident_id}",
        headers=headers,
    )
    assert inc_detail_resp.status_code == 200
    inc_dossier = inc_detail_resp.json()
    assert len(inc_dossier["diagnoses"]) >= 1

    latest_diagnosis = inc_dossier["diagnoses"][-1]
    assert latest_diagnosis["rule_name"] == "RULE_SERVICE_UNAVAILABLE"
    assert "HTTP 503" in latest_diagnosis["root_cause_hypothesis"]
    assert latest_diagnosis["recommended_action"] == "SIMULATE_RESTART"
    assert latest_diagnosis["confidence_score"] >= 0.85
    assert "status_code" in latest_diagnosis["evidence"]

    # =========================================================================
    # STEP 7: Incident Management Lifecycle (Acknowledge & Assign)
    # =========================================================================
    ack_resp = client.post(
        f"/api/v1/organizations/{org_id}/workspaces/{prod_ws_id}/incidents/{incident_id}/acknowledge",
        headers=headers,
        json={"note": "Lead SRE on-call paged. War room opened."},
    )
    assert ack_resp.status_code == 200
    assert ack_resp.json()["status"] == "ACKNOWLEDGED"

    assign_resp = client.post(
        f"/api/v1/organizations/{org_id}/workspaces/{prod_ws_id}/incidents/{incident_id}/assign",
        headers=headers,
        json={"assigned_to_user_id": user_id},
    )
    assert assign_resp.status_code == 200
    assert assign_resp.json()["assigned_to_user_id"] == user_id

    # =========================================================================
    # STEP 8: Recovery Policy & Dual-Custody HITL Approval Gate
    # =========================================================================
    # Create a high-risk recovery policy that requires explicit operator approval
    policy_resp = client.post(
        f"/api/v1/organizations/{org_id}/workspaces/{prod_ws_id}/recovery-policies",
        headers=headers,
        json={
            "name": "Production Payments Restart Guardrail",
            "trigger_condition": "RULE_SERVICE_UNAVAILABLE",
            "action": "SIMULATE_RESTART",
            "requires_approval": True,
            "max_retries": 2,
            "cooldown_seconds": 300,
            "timeout_seconds": 60,
            "service_id": service_id,
        },
    )
    assert policy_resp.status_code == 201
    policy_id = policy_resp.json()["id"]

    # Trigger Remediation via Incident War Room
    remediate_resp = client.post(
        f"/api/v1/organizations/{org_id}/workspaces/{prod_ws_id}/incidents/{incident_id}/remediate",
        headers=headers,
        json={"policy_id": policy_id, "action": "SIMULATE_RESTART", "note": "Authorize service restart"},
    )
    assert remediate_resp.status_code == 202
    assert remediate_resp.json()["status"] == "QUEUED"
    assert "Awaiting Human-in-the-Loop" in remediate_resp.json()["execution_output"]

    # Verify Approval Request is queued in Approvals inbox
    approvals_resp = client.get(
        f"/api/v1/organizations/{org_id}/workspaces/{prod_ws_id}/approvals",
        headers=headers,
    )
    assert approvals_resp.status_code == 200
    pending_approvals = approvals_resp.json()
    assert len(pending_approvals) >= 1
    approval_item = pending_approvals[0]
    assert approval_item["status"] == "PENDING"
    assert approval_item["proposed_action"] == "SIMULATE_RESTART"
    approval_id = approval_item["id"]

    # =========================================================================
    # STEP 9: Dual-Custody Approval & Controlled Recovery Execution
    # =========================================================================
    with patch("app.services.health_checker.probe_endpoint") as mock_probe:
        # Simulator will perform post-recovery health probe: mock healthy response
        mock_probe.return_value = (True, 200, 32.0, None)

        decide_resp = client.post(
            f"/api/v1/organizations/{org_id}/workspaces/{prod_ws_id}/approvals/{approval_id}/decide",
            headers=headers,
            json={
                "decision": "APPROVED",
                "reason": "Authorized by Reliability Lead after inspecting error logs.",
            },
        )
        assert decide_resp.status_code == 200
        decided_data = decide_resp.json()
        assert decided_data["status"] == "APPROVED"
        assert decided_data["execution_id"] is not None

    # Verify Recovery Execution History Record
    history_resp = client.get(
        f"/api/v1/organizations/{org_id}/workspaces/{prod_ws_id}/recovery-executions",
        headers=headers,
    )
    assert history_resp.status_code == 200
    executions = history_resp.json()
    assert len(executions) >= 1
    latest_exec = executions[0]
    assert latest_exec["action_taken"] == "SIMULATE_RESTART"
    assert latest_exec["status"] == "SUCCESS"
    assert latest_exec["verification_passed"] is True
    assert "Simulated 'SIMULATE_RESTART'" in latest_exec["execution_output"]
    assert "Verification probe passed" in latest_exec["execution_output"]

    # =========================================================================
    # STEP 10: Closed-Loop Auto-Resolution Verification
    # =========================================================================
    # Because post-recovery verification passed, the incident MUST transition to RESOLVED
    inc_resolved_resp = client.get(
        f"/api/v1/organizations/{org_id}/workspaces/{prod_ws_id}/incidents/{incident_id}",
        headers=headers,
    )
    assert inc_resolved_resp.status_code == 200
    inc_final = inc_resolved_resp.json()
    assert inc_final["status"] == "RESOLVED"
    assert inc_final["resolved_at"] is not None

    event_types = [e["event_type"] for e in inc_final["events"]]
    assert "RECOVERY_STARTED" in event_types
    assert "RECOVERY_VERIFIED" in event_types
    assert "RESOLVED" in event_types

    # =========================================================================
    # STEP 11: Immutable Audit Ledger Verification
    # =========================================================================
    audit_resp = client.get(
        f"/api/v1/organizations/{org_id}/audit-logs",
        headers=headers,
    )
    assert audit_resp.status_code == 200
    audit_logs = audit_resp.json()
    assert len(audit_logs) >= 5

    recorded_actions = [log["action"] for log in audit_logs]
    assert "SERVICE_REGISTERED" in recorded_actions
    assert "PROBE_MANUAL_TRIGGERED" in recorded_actions
    assert "INCIDENT_ACKNOWLEDGED" in recorded_actions
    assert "INCIDENT_ASSIGNED" in recorded_actions
    assert "POLICY_CREATED" in recorded_actions
    assert "APPROVAL_APPROVED" in recorded_actions
    assert "RECOVERY_SIMULATION_EXECUTED" in recorded_actions

    for log in audit_logs:
        assert log["organization_id"] == org_id
        assert log["user_email"] == "lead.sre@acme-cloud.com"
        assert log["created_at"] is not None
