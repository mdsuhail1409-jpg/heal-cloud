"""
Comprehensive Tests for HealCloud Incident Detection, Duplicate Prevention,
Explainable Diagnosis, Auto-Recovery, and Incident Management
"""

import uuid
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from app.models.incident import (
    Incident,
    IncidentEvent,
    Diagnosis,
    IncidentSeverityEnum,
    IncidentStatusEnum,
)
from app.models.service import Service, ServiceEndpoint, MonitoringCheck, MetricSample, HealthStatusEnum
from app.services.health_checker import execute_monitoring_check
from app.services.detection_engine import (
    process_monitoring_sample_for_incidents,
    run_explainable_diagnosis,
)


def _setup_org_and_workspace(client: TestClient, email: str):
    """Helper to register user, retrieve organization and workspace."""
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "SecurePassword123!",
            "full_name": "Reliability Tester",
            "organization_name": "Reliability Inc",
        },
    ).json()
    token = reg["access_token"]

    orgs = client.get("/api/v1/organizations", headers={"Authorization": f"Bearer {token}"}).json()
    org_id = orgs[0]["id"]

    workspaces = client.get(
        f"/api/v1/organizations/{org_id}/workspaces",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    ws_id = workspaces[0]["id"]

    return token, org_id, ws_id


def _create_service_with_check(client: TestClient, token: str, org_id: str, ws_id: str, name: str = "Auth API"):
    """Helper to create a service with an endpoint and monitoring check."""
    svc_resp = client.post(
        f"/api/v1/organizations/{org_id}/workspaces/{ws_id}/services",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": name,
            "description": "Authentication microservice",
            "endpoint_url": "https://api.github.com/status",
            "method": "GET",
            "expected_status_code": 200,
            "timeout_ms": 2000,
            "check_interval_seconds": 30,
            "consecutive_failure_threshold": 3,
        },
    )
    assert svc_resp.status_code == 201
    svc_data = svc_resp.json()
    return svc_data["id"], svc_data["endpoints"][0]["id"], svc_data["checks"][0]["id"]


def test_normal_conditions_no_incident_created(client: TestClient, db_session):
    """Test that healthy probe responses do not create incidents."""
    token, org_id, ws_id = _setup_org_and_workspace(client, "normal@reliability.io")
    svc_id, ep_id, chk_id = _create_service_with_check(client, token, org_id, ws_id, "Healthy Svc")

    with patch("app.services.health_checker.probe_endpoint") as mock_probe:
        mock_probe.return_value = (True, 200, 45.2, None)
        sample = execute_monitoring_check(uuid.UUID(chk_id), db_session)
        assert sample.is_successful is True

    # Check that no incidents were created
    incidents = db_session.query(Incident).filter(Incident.service_id == uuid.UUID(svc_id)).all()
    assert len(incidents) == 0


def test_service_unavailable_trigger_creates_p1_incident(client: TestClient, db_session):
    """Test Rule 1: Service unavailable (None status or connection failure) triggers critical incident."""
    token, org_id, ws_id = _setup_org_and_workspace(client, "unavail@reliability.io")
    svc_id, ep_id, chk_id = _create_service_with_check(client, token, org_id, ws_id, "Down Svc")

    with patch("app.services.health_checker.probe_endpoint") as mock_probe:
        # Connection error: status_code is None
        mock_probe.return_value = (False, None, 0.0, "Connection refused: port 443 closed")
        execute_monitoring_check(uuid.UUID(chk_id), db_session)

    incidents = db_session.query(Incident).filter(Incident.service_id == uuid.UUID(svc_id)).all()
    assert len(incidents) == 1
    inc = incidents[0]
    assert inc.severity == IncidentSeverityEnum.P1_CRITICAL.value
    assert inc.status == IncidentStatusEnum.OPEN.value
    assert "Service Unavailable" in inc.title

    # Verify explainable diagnosis
    assert len(inc.diagnoses) == 1
    diag = inc.diagnoses[0]
    assert diag.rule_name == "RULE_SERVICE_UNAVAILABLE"
    assert diag.confidence_score >= 0.85
    assert diag.recommended_action == "SIMULATE_RESTART"
    assert "Connection refused" in diag.evidence["error_message"]

    # Verify event history
    assert len(inc.events) == 2
    event_types = [e.event_type for e in inc.events]
    assert "DETECTED" in event_types
    assert "DIAGNOSED" in event_types


def test_repeated_health_check_failure_trigger(client: TestClient, db_session):
    """Test Rule 2: Consecutive failures crossing threshold triggers incident."""
    token, org_id, ws_id = _setup_org_and_workspace(client, "repeated@reliability.io")
    svc_id, ep_id, chk_id = _create_service_with_check(client, token, org_id, ws_id, "Failing Svc")

    with patch("app.services.health_checker.probe_endpoint") as mock_probe:
        # 1st failure (HTTP 404): degraded, failures=1 (threshold=3)
        mock_probe.return_value = (False, 404, 80.0, "Expected HTTP 200, received HTTP 404")
        execute_monitoring_check(uuid.UUID(chk_id), db_session)
        assert db_session.query(Incident).count() == 0

        # 2nd failure
        execute_monitoring_check(uuid.UUID(chk_id), db_session)
        assert db_session.query(Incident).count() == 0

        # 3rd failure: crosses threshold of 3!
        execute_monitoring_check(uuid.UUID(chk_id), db_session)

    incidents = db_session.query(Incident).filter(Incident.service_id == uuid.UUID(svc_id)).all()
    assert len(incidents) == 1
    inc = incidents[0]
    assert inc.severity == IncidentSeverityEnum.P2_HIGH.value
    assert "Repeated Health Check Failure" in inc.title
    assert inc.diagnoses[0].rule_name == "RULE_REPEATED_HEALTH_CHECK_FAILURE"


def test_response_time_threshold_exceeded_trigger(client: TestClient, db_session):
    """Test Rule 3: High latency sample triggers response-time exceeded incident."""
    token, org_id, ws_id = _setup_org_and_workspace(client, "latency@reliability.io")
    svc_id, ep_id, chk_id = _create_service_with_check(client, token, org_id, ws_id, "Slow Svc")

    with patch("app.services.health_checker.probe_endpoint") as mock_probe:
        # Latency 1900ms (> 80% of 2000ms timeout)
        mock_probe.return_value = (True, 200, 1900.0, None)
        execute_monitoring_check(uuid.UUID(chk_id), db_session)

    incidents = db_session.query(Incident).filter(Incident.service_id == uuid.UUID(svc_id)).all()
    assert len(incidents) == 1
    inc = incidents[0]
    assert inc.severity == IncidentSeverityEnum.P3_MEDIUM.value
    assert "Latency Degraded" in inc.title
    assert inc.diagnoses[0].rule_name == "RULE_RESPONSE_TIME_EXCEEDED"
    assert inc.diagnoses[0].recommended_action == "SIMULATE_SCALE_UP"


def test_excessive_consecutive_failures_trigger(client: TestClient, db_session):
    """Test Rule 4: 5 consecutive failures triggers critical excessive failure incident."""
    token, org_id, ws_id = _setup_org_and_workspace(client, "excessive@reliability.io")
    svc_id, ep_id, chk_id = _create_service_with_check(client, token, org_id, ws_id, "Broken Svc")

    svc = db_session.query(Service).filter(Service.id == uuid.UUID(svc_id)).first()
    svc.consecutive_failures = 4  # Next failure will make it 5

    with patch("app.services.health_checker.probe_endpoint") as mock_probe:
        mock_probe.return_value = (False, 500, 120.0, "Internal Server Error")
        execute_monitoring_check(uuid.UUID(chk_id), db_session)

    incidents = db_session.query(Incident).filter(Incident.service_id == uuid.UUID(svc_id)).all()
    assert len(incidents) == 1
    inc = incidents[0]
    assert inc.severity == IncidentSeverityEnum.P1_CRITICAL.value
    assert "Critical Outage" in inc.title
    assert inc.diagnoses[0].rule_name == "RULE_EXCESSIVE_CONSECUTIVE_FAILURES"


def test_recovery_verification_failure_trigger(client: TestClient, db_session):
    """Test Rule 5: Recovery verification failure triggers P1 incident with manual investigation recommendation."""
    token, org_id, ws_id = _setup_org_and_workspace(client, "recov_fail@reliability.io")
    svc_id, ep_id, chk_id = _create_service_with_check(client, token, org_id, ws_id, "Flaky Svc")

    service = db_session.query(Service).filter(Service.id == uuid.UUID(svc_id)).first()
    endpoint = db_session.query(ServiceEndpoint).filter(ServiceEndpoint.id == uuid.UUID(ep_id)).first()
    check = db_session.query(MonitoringCheck).filter(MonitoringCheck.id == uuid.UUID(chk_id)).first()

    sample = MetricSample(
        check_id=check.id,
        service_id=service.id,
        status_code=503,
        response_time_ms=500.0,
        is_successful=False,
        error_message="Service Unavailable post-restart",
    )
    db_session.add(sample)
    db_session.flush()

    inc, is_new = process_monitoring_sample_for_incidents(
        db=db_session,
        service=service,
        endpoint=endpoint,
        check=check,
        sample=sample,
        is_recovery_verification_failure=True,
        recovery_failure_details="Post-restart verification timeout: 503 Service Unavailable",
    )
    db_session.commit()

    assert inc is not None
    assert is_new is True
    assert inc.severity == IncidentSeverityEnum.P1_CRITICAL.value
    assert "Recovery Verification Failed" in inc.title
    assert inc.diagnoses[0].rule_name == "RULE_RECOVERY_VERIFICATION_FAILURE"
    assert inc.diagnoses[0].recommended_action == "MANUAL_INVESTIGATION"


def test_duplicate_incident_prevention_and_timeline_append(client: TestClient, db_session):
    """Test that repeated failures for an active incident do not spawn duplicates, but append events and escalate severity."""
    token, org_id, ws_id = _setup_org_and_workspace(client, "duplicate@reliability.io")
    svc_id, ep_id, chk_id = _create_service_with_check(client, token, org_id, ws_id, "Repeating Svc")

    with patch("app.services.health_checker.probe_endpoint") as mock_probe:
        # First failure triggers P2 incident
        mock_probe.return_value = (False, 502, 100.0, "Bad Gateway")
        execute_monitoring_check(uuid.UUID(chk_id), db_session)

        # Count incidents: exactly 1
        assert db_session.query(Incident).count() == 1

        # Second failure: should NOT create duplicate incident!
        mock_probe.return_value = (False, 502, 110.0, "Bad Gateway")
        execute_monitoring_check(uuid.UUID(chk_id), db_session)
        assert db_session.query(Incident).count() == 1

        # Third failure with critical condition (connection lost) - escalates severity
        mock_probe.return_value = (False, None, 0.0, "Connection refused")
        execute_monitoring_check(uuid.UUID(chk_id), db_session)
        assert db_session.query(Incident).count() == 1

    inc = db_session.query(Incident).first()
    assert inc.severity == IncidentSeverityEnum.P1_CRITICAL.value
    # Events should include DETECTED, DIAGNOSED, and THRESHOLD_BREACHED
    event_types = [e.event_type for e in inc.events]
    assert event_types.count("THRESHOLD_BREACHED") >= 2


def test_service_recovery_auto_resolves_active_incident(client: TestClient, db_session):
    """Test that returning to healthy state automatically marks an active incident as RESOLVED."""
    token, org_id, ws_id = _setup_org_and_workspace(client, "recovery@reliability.io")
    svc_id, ep_id, chk_id = _create_service_with_check(client, token, org_id, ws_id, "Recovering Svc")

    with patch("app.services.health_checker.probe_endpoint") as mock_probe:
        # Fail first to trigger incident
        mock_probe.return_value = (False, 500, 100.0, "Internal Server Error")
        execute_monitoring_check(uuid.UUID(chk_id), db_session)

        inc = db_session.query(Incident).first()
        assert inc.status == IncidentStatusEnum.OPEN.value

        # Now service recovers!
        mock_probe.return_value = (True, 200, 35.0, None)
        execute_monitoring_check(uuid.UUID(chk_id), db_session)

    db_session.refresh(inc)
    assert inc.status == IncidentStatusEnum.RESOLVED.value
    assert inc.resolved_at is not None

    event_types = [e.event_type for e in inc.events]
    assert "RESOLVED" in event_types


def test_explainable_diagnosis_does_not_invent_root_cause(client: TestClient, db_session):
    """Test that when evidence is ambiguous or nominal, diagnosis reports insufficient evidence."""
    token, org_id, ws_id = _setup_org_and_workspace(client, "honest_diag@reliability.io")
    svc_id, ep_id, chk_id = _create_service_with_check(client, token, org_id, ws_id, "Ambiguous Svc")

    # Manually create an incident without failure telemetry
    resp = client.post(
        f"/api/v1/organizations/{org_id}/workspaces/{ws_id}/incidents",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "service_id": svc_id,
            "title": "Manual investigation needed",
            "severity": "P3_MEDIUM",
        },
    )
    assert resp.status_code == 201
    inc_data = resp.json()
    incident_id = inc_data["id"]

    # Trigger on-demand diagnosis
    diag_resp = client.post(
        f"/api/v1/organizations/{org_id}/workspaces/{ws_id}/incidents/{incident_id}/diagnose",
        headers={"Authorization": f"Bearer {token}"},
        json={"force_re_evaluation": True},
    )
    assert diag_resp.status_code == 200
    diag = diag_resp.json()

    assert diag["rule_name"] == "RULE_INSUFFICIENT_EVIDENCE"
    assert "Insufficient telemetry evidence" in diag["root_cause_hypothesis"]
    assert diag["confidence_score"] <= 0.30
    assert diag["recommended_action"] == "MANUAL_INVESTIGATION"


def test_incident_lifecycle_acknowledge_assign_status_transitions(client: TestClient, db_session):
    """Test full incident lifecycle: acknowledge, assign to engineer, update status with validation."""
    token, org_id, ws_id = _setup_org_and_workspace(client, "lifecycle@reliability.io")
    svc_id, ep_id, chk_id = _create_service_with_check(client, token, org_id, ws_id, "Lifecycle Svc")

    # 1. Create incident
    resp = client.post(
        f"/api/v1/organizations/{org_id}/workspaces/{ws_id}/incidents",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "service_id": svc_id,
            "title": "Database connection pool exhausted",
            "severity": "P2_HIGH",
        },
    )
    assert resp.status_code == 201
    inc_id = resp.json()["id"]

    # 2. Acknowledge incident
    ack_resp = client.post(
        f"/api/v1/organizations/{org_id}/workspaces/{ws_id}/incidents/{inc_id}/acknowledge",
        headers={"Authorization": f"Bearer {token}"},
        json={"note": "Investigating active connection pools"},
    )
    assert ack_resp.status_code == 200
    assert ack_resp.json()["status"] == "ACKNOWLEDGED"
    assert ack_resp.json()["acknowledged_at"] is not None

    # 3. Assign incident to self
    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    my_user_id = me_resp.json()["user"]["id"]

    assign_resp = client.post(
        f"/api/v1/organizations/{org_id}/workspaces/{ws_id}/incidents/{inc_id}/assign",
        headers={"Authorization": f"Bearer {token}"},
        json={"assigned_to_user_id": my_user_id},
    )
    assert assign_resp.status_code == 200
    assert assign_resp.json()["assigned_to_user_id"] == my_user_id

    # 4. Status transition to INVESTIGATING
    stat_resp = client.patch(
        f"/api/v1/organizations/{org_id}/workspaces/{ws_id}/incidents/{inc_id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "INVESTIGATING"},
    )
    assert stat_resp.status_code == 200
    assert stat_resp.json()["status"] == "INVESTIGATING"

    # 5. Status transition to CLOSED
    close_resp = client.patch(
        f"/api/v1/organizations/{org_id}/workspaces/{ws_id}/incidents/{inc_id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "CLOSED"},
    )
    assert close_resp.status_code == 200
    assert close_resp.json()["status"] == "CLOSED"

    # 6. Invalid transition: CLOSED cannot transition directly to INVESTIGATING
    invalid_resp = client.patch(
        f"/api/v1/organizations/{org_id}/workspaces/{ws_id}/incidents/{inc_id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "INVESTIGATING"},
    )
    assert invalid_resp.status_code == 422


def test_cross_tenant_incident_isolation(client: TestClient, db_session):
    """Test that tenants cannot view, acknowledge, or modify incidents from other organizations."""
    token_a, org_a, ws_a = _setup_org_and_workspace(client, "alice@alpha.io")
    token_b, org_b, ws_b = _setup_org_and_workspace(client, "bob@beta.io")

    svc_id_a, _, _ = _create_service_with_check(client, token_a, org_a, ws_a, "Alpha Service")

    # Create incident in Org A
    inc_resp = client.post(
        f"/api/v1/organizations/{org_a}/workspaces/{ws_a}/incidents",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"service_id": svc_id_a, "title": "Alpha Outage"},
    )
    assert inc_resp.status_code == 201
    inc_id = inc_resp.json()["id"]

    # Bob (Org B) attempts to get Org A's incident -> Forbidden
    get_resp = client.get(
        f"/api/v1/organizations/{org_a}/workspaces/{ws_a}/incidents/{inc_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert get_resp.status_code == 403

    # Bob attempts to acknowledge Org A's incident -> Forbidden
    ack_resp = client.post(
        f"/api/v1/organizations/{org_a}/workspaces/{ws_a}/incidents/{inc_id}/acknowledge",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert ack_resp.status_code == 403
