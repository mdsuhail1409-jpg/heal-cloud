"""
Integration Tests for Health, Readiness, Metadata and Centralised Exception Handling
"""

from fastapi import status


def test_root_endpoint(client):
    """Verify root GET / returns welcome information and links."""
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "message" in data
    assert data["version"] == "0.1.0"
    assert "documentation" in data
    assert "health" in data


def test_liveness_probe(client):
    """Verify GET /api/v1/health/live returns alive status."""
    response = client.get("/api/v1/health/live")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "alive"
    assert "timestamp" in data


def test_readiness_probe(client):
    """Verify GET /api/v1/health/ready checks database and returns ready status."""
    response = client.get("/api/v1/health/ready")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "ready"
    assert "database" in data
    assert data["database"]["status"] == "healthy"
    assert data["database"]["database"] == "reachable"


def test_app_info_endpoint(client):
    """Verify GET /api/v1/health/info exposes correct application metadata."""
    response = client.get("/api/v1/health/info")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["project_name"] == "HealCloud"
    assert data["version"] == "0.1.0"
    assert data["api_prefix"] == "/api/v1"
    assert "environment" in data


def test_not_found_rfc7807_error(client):
    """Verify non-existent routes return RFC 7807 formatted Problem Details."""
    response = client.get("/api/v1/non-existent-endpoint")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert data["status"] == 404
    assert "title" in data
    assert "detail" in data
    assert "type" in data
    assert data["instance"] == "/api/v1/non-existent-endpoint"
    assert "timestamp" in data


def test_openapi_json(client):
    """Verify OpenAPI 3.0 documentation is auto-generated and valid."""
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == status.HTTP_200_OK
    schema = response.json()
    assert schema["openapi"].startswith("3.")
    assert "info" in schema
    assert schema["info"]["title"] == "HealCloud Platform API"
    assert "/api/v1/health/live" in schema["paths"]
    assert "/api/v1/health/ready" in schema["paths"]
    assert "/api/v1/health/info" in schema["paths"]
