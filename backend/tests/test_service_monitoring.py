"""
Automated Tests for Service Inventory, Configurable Health Checks, Metrics and Worker Execution
"""

from unittest.mock import patch
from fastapi import status

from app.models.service import HealthStatusEnum
from app.worker.runner import run_pending_checks


def _setup_org_and_workspace(client, email="sre@acme.io"):
    """Helper to register user, create organization and return auth token & IDs."""
    reg = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "SecurePassword123!",
        "full_name": "SRE Engineer",
        "organization_name": "Acme Cloud Org",
    }).json()
    token = reg["access_token"]

    orgs = client.get("/api/v1/organizations", headers={"Authorization": f"Bearer {token}"}).json()
    org_id = orgs[0]["id"]

    workspaces = client.get(
        f"/api/v1/organizations/{org_id}/workspaces",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    ws_id = workspaces[0]["id"]

    return token, org_id, ws_id


def test_register_service_success(client):
    """Test successful service registration with endpoint and health check."""
    token, org_id, ws_id = _setup_org_and_workspace(client, "sre1@acme.io")

    payload = {
        "name": "Payment Gateway API",
        "description": "Critical payment processing microservice",
        "endpoint_url": "https://api.github.com/status",
        "method": "GET",
        "expected_status_code": 200,
        "timeout_ms": 3000,
        "check_interval_seconds": 15,
        "consecutive_failure_threshold": 3,
    }

    response = client.post(
        f"/api/v1/organizations/{org_id}/workspaces/{ws_id}/services",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "Payment Gateway API"
    assert data["health_status"] == HealthStatusEnum.UNKNOWN.value
    assert data["consecutive_failures"] == 0
    assert len(data["endpoints"]) == 1
    assert data["endpoints"][0]["url"] == "https://api.github.com/status"
    assert len(data["checks"]) == 1
    assert data["checks"][0]["interval_seconds"] == 15


def test_register_duplicate_service_fails(client):
    """Test registering a service with an existing name in the same workspace returns 409 Conflict."""
    token, org_id, ws_id = _setup_org_and_workspace(client, "sre2@acme.io")
    payload = {
        "name": "Auth Service",
        "endpoint_url": "https://api.github.com/auth",
        "expected_status_code": 200,
    }
    r1 = client.post(
        f"/api/v1/organizations/{org_id}/workspaces/{ws_id}/services",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert r1.status_code == status.HTTP_201_CREATED

    r2 = client.post(
        f"/api/v1/organizations/{org_id}/workspaces/{ws_id}/services",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert r2.status_code == status.HTTP_409_CONFLICT
    assert "already registered" in r2.json()["detail"]


def test_cross_tenant_service_isolation(client):
    """Test that a user in Org A cannot access or probe services in Org B."""
    token_a, org_a_id, ws_a_id = _setup_org_and_workspace(client, "alice@org-a.io")
    token_b, org_b_id, ws_b_id = _setup_org_and_workspace(client, "bob@org-b.io")

    # Bob registers a service in Org B
    service_b = client.post(
        f"/api/v1/organizations/{org_b_id}/workspaces/{ws_b_id}/services",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"name": "Bob Service", "endpoint_url": "https://api.github.com/zen"},
    ).json()

    # Alice tries to read Bob's service in Org B -> 403 Forbidden
    cross_read = client.get(
        f"/api/v1/organizations/{org_b_id}/workspaces/{ws_b_id}/services/{service_b['id']}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert cross_read.status_code == status.HTTP_403_FORBIDDEN

    # Alice tries to trigger probe on Bob's service -> 403 Forbidden
    cross_probe = client.post(
        f"/api/v1/organizations/{org_b_id}/workspaces/{ws_b_id}/services/{service_b['id']}/checks/run",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert cross_probe.status_code == status.HTTP_403_FORBIDDEN


def test_rbac_service_registration_restrictions(client):
    """Test role hierarchy: VIEWER cannot register services."""
    owner_token, org_id, ws_id = _setup_org_and_workspace(client, "owner@acme-rbac.io")

    # Register Viewer user
    viewer_reg = client.post("/api/v1/auth/register", json={
        "email": "viewer@acme-rbac.io",
        "password": "SecurePassword123!",
        "full_name": "Viewer Only",
    }).json()
    viewer_token = viewer_reg["access_token"]

    # Add viewer to organization with VIEWER role
    client.post(
        f"/api/v1/organizations/{org_id}/memberships",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"email": "viewer@acme-rbac.io", "role": "VIEWER"},
    )

    # Viewer attempts to register a service -> 403 Forbidden
    resp = client.post(
        f"/api/v1/organizations/{org_id}/workspaces/{ws_id}/services",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={"name": "Forbidden Service", "endpoint_url": "https://api.github.com/status"},
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN
    assert "requires at least 'RELIABILITY_ENGINEER'" in resp.json()["detail"]


@patch("app.services.health_checker.probe_endpoint")
def test_health_check_execution_lifecycle(mock_probe, client):
    """Test health check execution transitioning from UNKNOWN -> HEALTHY -> DEGRADED -> UNHEALTHY."""
    token, org_id, ws_id = _setup_org_and_workspace(client, "lifecycle@acme.io")

    service = client.post(
        f"/api/v1/organizations/{org_id}/workspaces/{ws_id}/services",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Lifecycle Service",
            "endpoint_url": "https://api.github.com/status",
            "expected_status_code": 200,
            "consecutive_failure_threshold": 3,
        },
    ).json()
    srv_id = service["id"]

    # 1. Successful check (200 OK) -> HEALTHY
    mock_probe.return_value = (True, 200, 42.5, None)
    probe_1 = client.post(
        f"/api/v1/organizations/{org_id}/workspaces/{ws_id}/services/{srv_id}/checks/run",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    assert probe_1["is_successful"] is True
    assert probe_1["health_status"] == HealthStatusEnum.HEALTHY.value
    assert probe_1["consecutive_failures"] == 0

    # 2. Failing check 1 (500 Error) -> DEGRADED (1 failure < threshold 3)
    mock_probe.return_value = (False, 500, 85.0, "Expected HTTP 200, received HTTP 500.")
    probe_2 = client.post(
        f"/api/v1/organizations/{org_id}/workspaces/{ws_id}/services/{srv_id}/checks/run",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    assert probe_2["is_successful"] is False
    assert probe_2["health_status"] == HealthStatusEnum.DEGRADED.value
    assert probe_2["consecutive_failures"] == 1

    # 3. Failing check 2 -> DEGRADED (2 failures < threshold 3)
    probe_3 = client.post(
        f"/api/v1/organizations/{org_id}/workspaces/{ws_id}/services/{srv_id}/checks/run",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    assert probe_3["health_status"] == HealthStatusEnum.DEGRADED.value
    assert probe_3["consecutive_failures"] == 2

    # 4. Failing check 3 -> UNHEALTHY (3 failures >= threshold 3)
    probe_4 = client.post(
        f"/api/v1/organizations/{org_id}/workspaces/{ws_id}/services/{srv_id}/checks/run",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    assert probe_4["health_status"] == HealthStatusEnum.UNHEALTHY.value
    assert probe_4["consecutive_failures"] == 3

    # 5. Check persistent metric history recorded 4 samples
    metrics_resp = client.get(
        f"/api/v1/organizations/{org_id}/workspaces/{ws_id}/services/{srv_id}/metrics",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert metrics_resp.status_code == status.HTTP_200_OK
    samples = metrics_resp.json()
    assert len(samples) == 4


@patch("app.services.health_checker.probe_endpoint")
def test_worker_background_execution(mock_probe, client):
    """Test worker run_pending_checks detects due checks and executes probes."""
    token, org_id, ws_id = _setup_org_and_workspace(client, "worker@acme.io")

    client.post(
        f"/api/v1/organizations/{org_id}/workspaces/{ws_id}/services",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Background Checked Service",
            "endpoint_url": "https://api.github.com/zen",
            "expected_status_code": 200,
            "check_interval_seconds": 10,
        },
    )

    mock_probe.return_value = (True, 200, 35.0, None)

    # Execute worker cycle
    executed = run_pending_checks(max_checks=10)
    assert executed >= 1

    # Re-run immediately: interval not yet elapsed, so 0 checks should be due
    executed_again = run_pending_checks(max_checks=10)
    assert executed_again == 0


def test_prometheus_metrics_endpoint(client):
    """Test GET /api/v1/metrics outputs standard Prometheus plaintext format."""
    response = client.get("/api/v1/metrics")
    assert response.status_code == status.HTTP_200_OK
    assert "text/plain" in response.headers["content-type"]
    body = response.text
    assert "# HELP healcloud_services_total" in body
    assert "# TYPE healcloud_services_total gauge" in body
    assert "# HELP healcloud_health_probes_total" in body
