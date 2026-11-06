"""
Automated Tests for Authentication, Registration, Password Management and Token Security
"""

import time
from datetime import timedelta
import jwt
from fastapi import status

from app.core.config import settings
from app.core.security import create_access_token, reset_login_failures


def test_register_success(client):
    """Test successful user registration without organization."""
    payload = {
        "email": "user1@healcloud.io",
        "password": "SecurePassword123!",
        "full_name": "Test User One",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "user1@healcloud.io"
    assert data["user"]["full_name"] == "Test User One"
    assert "password" not in data["user"]
    assert "password_hash" not in data["user"]


def test_register_with_organization(client):
    """Test user registration with automatic organization and workspace creation."""
    payload = {
        "email": "owner@acme.io",
        "password": "SecurePassword123!",
        "full_name": "Acme Owner",
        "organization_name": "Acme Corporation",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    token = data["access_token"]

    # Verify profile reflects new organization with ORG_OWNER role
    profile_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert profile_resp.status_code == status.HTTP_200_OK
    profile = profile_resp.json()
    assert len(profile["memberships"]) == 1
    assert profile["memberships"][0]["organization_name"] == "Acme Corporation"
    assert profile["memberships"][0]["role"] == "ORG_OWNER"


def test_register_duplicate_email_fails(client):
    """Test duplicate registration returns 409 Conflict."""
    payload = {
        "email": "duplicate@healcloud.io",
        "password": "SecurePassword123!",
        "full_name": "Original User",
    }
    r1 = client.post("/api/v1/auth/register", json=payload)
    assert r1.status_code == status.HTTP_201_CREATED

    r2 = client.post("/api/v1/auth/register", json=payload)
    assert r2.status_code == status.HTTP_409_CONFLICT
    err = r2.json()
    assert err["status"] == 409
    assert "already exists" in err["detail"]


def test_login_success(client):
    """Test valid user login generates signed JWT token."""
    # Register user first
    client.post("/api/v1/auth/register", json={
        "email": "loginuser@healcloud.io",
        "password": "CorrectPassword123!",
        "full_name": "Login User",
    })

    # Perform valid login
    response = client.post("/api/v1/auth/login", json={
        "email": "loginuser@healcloud.io",
        "password": "CorrectPassword123!",
    })
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "loginuser@healcloud.io"


def test_login_invalid_password_fails(client):
    """Test login with wrong password returns 401 Unauthorized."""
    client.post("/api/v1/auth/register", json={
        "email": "wrongpwd@healcloud.io",
        "password": "CorrectPassword123!",
        "full_name": "Wrong Pwd User",
    })

    response = client.post("/api/v1/auth/login", json={
        "email": "wrongpwd@healcloud.io",
        "password": "WrongPassword999!",
    })
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    err = response.json()
    assert err["status"] == 401
    assert "Invalid email address or password" in err["detail"]


def test_login_nonexistent_email_fails(client):
    """Test login with non-existent email returns 401 Unauthorized without user enumeration."""
    response = client.post("/api/v1/auth/login", json={
        "email": "nonexistent@healcloud.io",
        "password": "SomePassword123!",
    })
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Invalid email address or password" in response.json()["detail"]


def test_login_rate_limiting(client):
    """Test rate limiting triggers 429 Too Many Requests after consecutive failures."""
    email = "ratelimited@healcloud.io"
    # Ensure fresh state
    reset_login_failures(f"testclient:{email}")

    # Exhaust permitted login attempts
    for _ in range(settings.RATE_LIMIT_LOGIN_ATTEMPTS):
        resp = client.post("/api/v1/auth/login", json={"email": email, "password": "WrongPassword1!"})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    # Next attempt should be blocked by rate limit
    blocked_resp = client.post("/api/v1/auth/login", json={"email": email, "password": "WrongPassword1!"})
    assert blocked_resp.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert blocked_resp.json()["status"] == 429


def test_unauthorized_access_missing_token(client):
    """Test accessing protected route without Authorization header returns 401."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    err = response.json()
    assert err["status"] == 401
    assert "Not authenticated" in err["detail"]


def test_unauthorized_access_invalid_token(client):
    """Test accessing protected route with forged or malformed token returns 401."""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer forged-invalid-token-signature"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Invalid access token" in response.json()["detail"]


def test_unauthorized_access_expired_token(client):
    """Test access with expired token returns 401 with expiration detail."""
    # Create an expired token manually
    expired_token = create_access_token(
        subject="00000000-0000-0000-0000-000000000001",
        expires_delta=timedelta(seconds=-10),
    )
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "expired" in response.json()["detail"].lower()


def test_change_password(client):
    """Test password update and re-authentication with new credentials."""
    # Register user
    reg = client.post("/api/v1/auth/register", json={
        "email": "pwdchange@healcloud.io",
        "password": "OldPassword123!",
        "full_name": "Password Changer",
    }).json()
    token = reg["access_token"]

    # 1. Attempt with incorrect current password -> 401
    fail_resp = client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "WrongCurrentPassword123!",
            "new_password": "NewSecurePassword456!",
        },
    )
    assert fail_resp.status_code == status.HTTP_401_UNAUTHORIZED

    # 2. Change with correct current password -> 200
    success_resp = client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "OldPassword123!",
            "new_password": "NewSecurePassword456!",
        },
    )
    assert success_resp.status_code == status.HTTP_200_OK

    # 3. Login with old password fails
    old_login = client.post("/api/v1/auth/login", json={
        "email": "pwdchange@healcloud.io",
        "password": "OldPassword123!",
    })
    assert old_login.status_code == status.HTTP_401_UNAUTHORIZED

    # 4. Login with new password succeeds
    new_login = client.post("/api/v1/auth/login", json={
        "email": "pwdchange@healcloud.io",
        "password": "NewSecurePassword456!",
    })
    assert new_login.status_code == status.HTTP_200_OK
