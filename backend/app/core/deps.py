"""
Authentication, Multi-Tenant Scoping and RBAC FastAPI Dependencies
"""

import uuid
from typing import Optional, Callable
from dataclasses import dataclass
from fastapi import Depends, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.core.exceptions import (
    UnauthorizedException,
    ForbiddenException,
    EntityNotFoundException,
)
from app.db.session import get_db
from app.models.user import User
from app.models.organization import Organization
from app.models.membership import Membership, RoleEnum

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False,
)


@dataclass
class TenantContext:
    """Encapsulates the verified tenant, current user, and evaluated role."""
    organization: Organization
    user: User
    role: RoleEnum
    membership: Optional[Membership] = None


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """
    Extract and verify JWT bearer token from Authorization header or OAuth2 scheme.
    Denies access by default if token is missing, invalid, or expired.
    """
    raw_token = token
    if not raw_token and authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            raw_token = parts[1]

    if not raw_token:
        raise UnauthorizedException("Not authenticated. Please provide a valid Bearer token.")

    payload = decode_access_token(raw_token)
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedException("Malformed token: Subject identifier missing.")

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise UnauthorizedException("Malformed token: Subject identifier is not a valid UUID.")

    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise UnauthorizedException("User account associated with this token no longer exists.")

    if not user.is_active:
        raise UnauthorizedException("User account has been deactivated.")

    return user


def get_current_platform_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require user to be a global platform administrator."""
    if not current_user.is_platform_admin:
        raise ForbiddenException("Platform administrator privileges required for this operation.")
    return current_user


def get_tenant_context(
    org_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TenantContext:
    """
    Verifies that the authenticated user belongs to the requested organization.
    Prevents cross-tenant data leaks and unauthorized access by validating membership on every call.
    """
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org or not org.is_active:
        raise EntityNotFoundException("Organization", org_id)

    # Platform Admins bypass organization membership restriction with OWNER capabilities
    if current_user.is_platform_admin:
        return TenantContext(
            organization=org,
            user=current_user,
            role=RoleEnum.ORG_OWNER,
            membership=None,
        )

    # Look up direct organization membership
    membership = (
        db.query(Membership)
        .filter(
            Membership.organization_id == org_id,
            Membership.user_id == current_user.id,
        )
        .first()
    )

    if not membership:
        raise ForbiddenException("Access denied: You are not a member of this organization.")

    user_role = RoleEnum(membership.role)
    return TenantContext(
        organization=org,
        user=current_user,
        role=user_role,
        membership=membership,
    )


def require_role(min_role: RoleEnum) -> Callable[[TenantContext], TenantContext]:
    """
    Dependency factory enforcing role hierarchy on tenant-scoped operations.
    Example: Depends(require_role(RoleEnum.ORG_ADMIN))
    """
    def role_checker(
        tenant_ctx: TenantContext = Depends(get_tenant_context),
    ) -> TenantContext:
        if not tenant_ctx.role.has_permission(min_role):
            raise ForbiddenException(
                f"Action requires at least '{min_role.value}' role in organization '{tenant_ctx.organization.name}'. "
                f"Your assigned role is '{tenant_ctx.role.value}'."
            )
        return tenant_ctx

    return role_checker
