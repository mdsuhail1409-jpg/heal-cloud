"""
Automated Tests for Multi-Tenant Data Isolation, RBAC Role Hierarchies and Cross-Tenant Protection
"""

import uuid
from fastapi import status
from app.models.membership import RoleEnum


def _create_user_and_token(client, email: str, name: str, org_name: str = None) -> tuple:
    payload = {
        "email": email,
        "password": "SecurePassword123!",
        "full_name": name,
    }
    if org_name:
        payload["organization_name"] = org_name

    resp = client.post("/api/v1/auth/register", json=payload)
    data = resp.json()
    return data["user"], data["access_token"]


def test_organization_creation_assigns_owner(client):
    """Verify organization creation assigns ORG_OWNER role and creates default workspace."""
    user, token = _create_user_and_token(client, "orgowner@test.io", "Org Owner")

    resp = client.post(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Alpha Corp", "slug": "alpha-corp"},
    )
    assert resp.status_code == status.HTTP_201_CREATED
    org = resp.json()
    assert org["name"] == "Alpha Corp"
    assert org["slug"] == "alpha-corp"
    assert org["user_role"] == "ORG_OWNER"

    # Verify default workspace exists
    ws_resp = client.get(
        f"/api/v1/organizations/{org['id']}/workspaces",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ws_resp.status_code == status.HTTP_200_OK
    workspaces = ws_resp.json()
    assert len(workspaces) == 1
    assert workspaces[0]["slug"] == "production"


def test_cross_tenant_organization_isolation(client):
    """Test that a user from Org A cannot read or modify Org B."""
    # Org A Owner
    user_a, token_a = _create_user_and_token(client, "user_a@tenant.io", "User A", "Org Alpha")
    # Org B Owner
    user_b, token_b = _create_user_and_token(client, "user_b@tenant.io", "User B", "Org Beta")

    # Fetch Org B details
    org_b_list = client.get("/api/v1/organizations", headers={"Authorization": f"Bearer {token_b}"}).json()
    org_b_id = org_b_list[0]["id"]

    # User A tries to view Org B -> 403 Forbidden
    cross_read = client.get(
        f"/api/v1/organizations/{org_b_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert cross_read.status_code == status.HTTP_403_FORBIDDEN
    assert "not a member" in cross_read.json()["detail"]

    # User A tries to update Org B -> 403 Forbidden
    cross_update = client.put(
        f"/api/v1/organizations/{org_b_id}",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"name": "Hacked Org Name"},
    )
    assert cross_update.status_code == status.HTTP_403_FORBIDDEN


def test_cross_tenant_workspace_isolation(client):
    """Test that User A cannot access or create workspaces inside Org B."""
    _, token_a = _create_user_and_token(client, "alice@alpha.io", "Alice", "Org Alpha")
    _, token_b = _create_user_and_token(client, "bob@beta.io", "Bob", "Org Beta")

    # Get Org B and its workspace ID
    org_b = client.get("/api/v1/organizations", headers={"Authorization": f"Bearer {token_b}"}).json()[0]
    org_b_id = org_b["id"]
    ws_b = client.get(f"/api/v1/organizations/{org_b_id}/workspaces", headers={"Authorization": f"Bearer {token_b}"}).json()[0]
    ws_b_id = ws_b["id"]

    # Alice attempts to access Bob's workspace in Org B -> 403 Forbidden
    cross_ws_read = client.get(
        f"/api/v1/organizations/{org_b_id}/workspaces/{ws_b_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert cross_ws_read.status_code == status.HTTP_403_FORBIDDEN

    # Alice attempts to create a workspace in Org B -> 403 Forbidden
    cross_ws_create = client.post(
        f"/api/v1/organizations/{org_b_id}/workspaces",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"name": "Alice Infiltration Workspace", "slug": "alice-infiltrate"},
    )
    assert cross_ws_create.status_code == status.HTTP_403_FORBIDDEN


def test_rbac_workspace_creation_restrictions(client):
    """Test role hierarchy: ORG_ADMIN/OWNER can create workspace, but VIEWER cannot."""
    # Create Organization with Owner
    _, owner_token = _create_user_and_token(client, "lead@acme.io", "Lead Owner", "RBAC Test Org")
    org = client.get("/api/v1/organizations", headers={"Authorization": f"Bearer {owner_token}"}).json()[0]
    org_id = org["id"]

    # Create Viewer user
    viewer_user, viewer_token = _create_user_and_token(client, "viewer@acme.io", "Viewer User")

    # Add viewer to organization with VIEWER role
    add_resp = client.post(
        f"/api/v1/organizations/{org_id}/memberships",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"email": "viewer@acme.io", "role": "VIEWER"},
    )
    assert add_resp.status_code == status.HTTP_201_CREATED

    # Viewer can read workspaces -> 200 OK
    read_resp = client.get(
        f"/api/v1/organizations/{org_id}/workspaces",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert read_resp.status_code == status.HTTP_200_OK

    # Viewer attempts to create workspace -> 403 Forbidden
    create_resp = client.post(
        f"/api/v1/organizations/{org_id}/workspaces",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={"name": "Viewer Sandbox", "slug": "viewer-sandbox"},
    )
    assert create_resp.status_code == status.HTTP_403_FORBIDDEN
    assert "requires at least 'ORG_ADMIN'" in create_resp.json()["detail"]


def test_rbac_member_management_restrictions(client):
    """Test that ORG_ADMIN cannot assign or modify ORG_OWNER, and cannot demote sole owner."""
    _, owner_token = _create_user_and_token(client, "superowner@org.io", "Super Owner", "Governance Org")
    org = client.get("/api/v1/organizations", headers={"Authorization": f"Bearer {owner_token}"}).json()[0]
    org_id = org["id"]

    # Register admin user and engineer user
    _, admin_token = _create_user_and_token(client, "admin@org.io", "Admin User")
    _, eng_token = _create_user_and_token(client, "eng@org.io", "Engineer User")

    # Owner adds Admin with ORG_ADMIN role
    client.post(
        f"/api/v1/organizations/{org_id}/memberships",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"email": "admin@org.io", "role": "ORG_ADMIN"},
    )

    # Admin attempts to add another user as ORG_OWNER -> 403 Forbidden
    admin_grant_owner = client.post(
        f"/api/v1/organizations/{org_id}/memberships",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"email": "eng@org.io", "role": "ORG_OWNER"},
    )
    assert admin_grant_owner.status_code == status.HTTP_403_FORBIDDEN
    assert "Only an Organization Owner can grant the ORG_OWNER role" in admin_grant_owner.json()["detail"]

    # Admin can add engineer as RELIABILITY_ENGINEER -> 201 Created
    admin_grant_eng = client.post(
        f"/api/v1/organizations/{org_id}/memberships",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"email": "eng@org.io", "role": "RELIABILITY_ENGINEER"},
    )
    assert admin_grant_eng.status_code == status.HTTP_201_CREATED

    # Attempt to demote sole owner -> Validation error
    members = client.get(f"/api/v1/organizations/{org_id}/memberships", headers={"Authorization": f"Bearer {owner_token}"}).json()
    owner_membership = [m for m in members if m["role"] == "ORG_OWNER"][0]

    demote_sole_owner = client.put(
        f"/api/v1/organizations/{org_id}/memberships/{owner_membership['id']}",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"role": "VIEWER"},
    )
    assert demote_sole_owner.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "Cannot demote the sole Organization Owner" in demote_sole_owner.json()["detail"]
