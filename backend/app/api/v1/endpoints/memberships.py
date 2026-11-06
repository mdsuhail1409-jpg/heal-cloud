"""
Organization Membership & RBAC API Endpoints (Tenant-Scoped)
"""

import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictException,
    EntityNotFoundException,
    ForbiddenException,
    ValidationException,
)
from app.core.deps import (
    require_role,
    TenantContext,
)
from app.db.session import get_db
from app.models.user import User
from app.models.membership import Membership, RoleEnum
from app.schemas.membership import (
    MembershipCreate,
    MembershipUpdate,
    MembershipRead,
)

router = APIRouter(prefix="/organizations/{org_id}/memberships", tags=["Memberships & RBAC"])


@router.get(
    "",
    response_model=List[MembershipRead],
    status_code=status.HTTP_200_OK,
    summary="List Organization Members",
    description="Returns all registered members and their roles within the organization.",
)
def list_memberships(
    org_id: uuid.UUID,
    tenant_ctx: TenantContext = Depends(require_role(RoleEnum.VIEWER)),
    db: Session = Depends(get_db),
) -> List[MembershipRead]:
    members = (
        db.query(Membership)
        .join(User, Membership.user_id == User.id)
        .filter(Membership.organization_id == org_id)
        .order_by(Membership.created_at.asc())
        .all()
    )

    return [
        MembershipRead(
            id=m.id,
            organization_id=m.organization_id,
            user_id=m.user_id,
            role=m.role,
            user_email=m.user.email,
            user_full_name=m.user.full_name,
            created_at=m.created_at,
        )
        for m in members
    ]


@router.post(
    "",
    response_model=MembershipRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add Member to Organization",
    description="Adds an existing user to the organization with a specified role. Requires ORG_ADMIN or ORG_OWNER.",
)
def add_membership(
    org_id: uuid.UUID,
    req: MembershipCreate,
    tenant_ctx: TenantContext = Depends(require_role(RoleEnum.ORG_ADMIN)),
    db: Session = Depends(get_db),
) -> MembershipRead:
    # Only ORG_OWNER can assign ORG_OWNER role to another user
    if req.role == RoleEnum.ORG_OWNER and tenant_ctx.role != RoleEnum.ORG_OWNER:
        raise ForbiddenException("Only an Organization Owner can grant the ORG_OWNER role.")

    # Locate user by email
    target_user = db.query(User).filter(User.email == req.email.lower()).first()
    if not target_user:
        raise EntityNotFoundException("User with email", req.email)

    # Check if user is already a member
    existing = (
        db.query(Membership)
        .filter(
            Membership.organization_id == org_id,
            Membership.user_id == target_user.id,
        )
        .first()
    )
    if existing:
        raise ConflictException(
            f"User '{req.email}' is already a member of this organization with role '{existing.role}'.",
            details={"email": req.email, "role": existing.role},
        )

    membership = Membership(
        organization_id=org_id,
        user_id=target_user.id,
        role=req.role.value,
    )
    db.add(membership)
    db.flush()

    return MembershipRead(
        id=membership.id,
        organization_id=membership.organization_id,
        user_id=membership.user_id,
        role=membership.role,
        user_email=target_user.email,
        user_full_name=target_user.full_name,
        created_at=membership.created_at,
    )


@router.put(
    "/{membership_id}",
    response_model=MembershipRead,
    status_code=status.HTTP_200_OK,
    summary="Update Member Role",
    description="Modifies the role assigned to an existing organization member.",
)
def update_membership_role(
    org_id: uuid.UUID,
    membership_id: uuid.UUID,
    req: MembershipUpdate,
    tenant_ctx: TenantContext = Depends(require_role(RoleEnum.ORG_ADMIN)),
    db: Session = Depends(get_db),
) -> MembershipRead:
    membership = (
        db.query(Membership)
        .filter(
            Membership.id == membership_id,
            Membership.organization_id == org_id,
        )
        .first()
    )
    if not membership:
        raise EntityNotFoundException("Membership", membership_id)

    # Prevent non-owners from promoting or demoting owners
    if (membership.role == RoleEnum.ORG_OWNER.value or req.role == RoleEnum.ORG_OWNER) and tenant_ctx.role != RoleEnum.ORG_OWNER:
        raise ForbiddenException("Only an Organization Owner can modify ORG_OWNER roles.")

    # Guard: prevent demoting the sole ORG_OWNER
    if membership.role == RoleEnum.ORG_OWNER.value and req.role != RoleEnum.ORG_OWNER:
        owner_count = (
            db.query(Membership)
            .filter(
                Membership.organization_id == org_id,
                Membership.role == RoleEnum.ORG_OWNER.value,
            )
            .count()
        )
        if owner_count <= 1:
            raise ValidationException("Cannot demote the sole Organization Owner. Transfer ownership first.")

    membership.role = req.role.value
    db.add(membership)

    return MembershipRead(
        id=membership.id,
        organization_id=membership.organization_id,
        user_id=membership.user_id,
        role=membership.role,
        user_email=membership.user.email,
        user_full_name=membership.user.full_name,
        created_at=membership.created_at,
    )


@router.delete(
    "/{membership_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove Member from Organization",
    description="Revokes access for a member from the organization. Requires ORG_ADMIN or ORG_OWNER.",
)
def remove_membership(
    org_id: uuid.UUID,
    membership_id: uuid.UUID,
    tenant_ctx: TenantContext = Depends(require_role(RoleEnum.ORG_ADMIN)),
    db: Session = Depends(get_db),
) -> dict:
    membership = (
        db.query(Membership)
        .filter(
            Membership.id == membership_id,
            Membership.organization_id == org_id,
        )
        .first()
    )
    if not membership:
        raise EntityNotFoundException("Membership", membership_id)

    # Prevent non-owners from removing owners
    if membership.role == RoleEnum.ORG_OWNER.value and tenant_ctx.role != RoleEnum.ORG_OWNER:
        raise ForbiddenException("Only an Organization Owner can remove an ORG_OWNER from the organization.")

    # Guard: prevent removing the sole ORG_OWNER
    if membership.role == RoleEnum.ORG_OWNER.value:
        owner_count = (
            db.query(Membership)
            .filter(
                Membership.organization_id == org_id,
                Membership.role == RoleEnum.ORG_OWNER.value,
            )
            .count()
        )
        if owner_count <= 1:
            raise ValidationException("Cannot remove the sole Organization Owner. Transfer ownership first.")

    db.delete(membership)
    return {
        "message": f"User '{membership.user.email}' removed from organization.",
        "membership_id": str(membership_id),
    }

