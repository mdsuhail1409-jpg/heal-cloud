"""
Organization Management API Endpoints
"""

import re
import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException
from app.core.deps import (
    get_current_user,
    get_tenant_context,
    require_role,
    TenantContext,
)
from app.db.session import get_db
from app.models.user import User
from app.models.organization import Organization, Workspace
from app.models.membership import Membership, RoleEnum
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationRead,
)

router = APIRouter(prefix="/organizations", tags=["Organizations"])


def _slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", slug)


@router.post(
    "",
    response_model=OrganizationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Organization",
    description="Provisions a new organization. The creator is automatically assigned as ORG_OWNER.",
)
def create_organization(
    req: OrganizationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrganizationRead:
    slug = req.slug or _slugify(req.name)
    existing = db.query(Organization).filter(Organization.slug == slug).first()
    if existing:
        raise ConflictException(
            f"An organization with slug '{slug}' already exists.",
            details={"slug": slug},
        )

    org = Organization(
        name=req.name,
        slug=slug,
        is_active=True,
    )
    db.add(org)
    db.flush()

    # Assign creator as ORG_OWNER
    membership = Membership(
        organization_id=org.id,
        user_id=current_user.id,
        role=RoleEnum.ORG_OWNER.value,
    )
    db.add(membership)

    # Provision default workspace
    default_ws = Workspace(
        organization_id=org.id,
        name="Production",
        slug="production",
        description="Default production environment workspace",
    )
    db.add(default_ws)

    return OrganizationRead(
        id=org.id,
        name=org.name,
        slug=org.slug,
        is_active=org.is_active,
        created_at=org.created_at,
        user_role=RoleEnum.ORG_OWNER.value,
    )


@router.get(
    "",
    response_model=List[OrganizationRead],
    status_code=status.HTTP_200_OK,
    summary="List Organizations",
    description="Returns all active organizations accessible to the authenticated user.",
)
def list_organizations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[OrganizationRead]:
    if current_user.is_platform_admin:
        orgs = db.query(Organization).filter(Organization.is_active.is_(True)).all()
        return [
            OrganizationRead(
                id=o.id,
                name=o.name,
                slug=o.slug,
                is_active=o.is_active,
                created_at=o.created_at,
                user_role="PLATFORM_ADMIN",
            )
            for o in orgs
        ]

    memberships = (
        db.query(Membership)
        .join(Organization, Membership.organization_id == Organization.id)
        .filter(Membership.user_id == current_user.id, Organization.is_active.is_(True))
        .all()
    )

    return [
        OrganizationRead(
            id=m.organization.id,
            name=m.organization.name,
            slug=m.organization.slug,
            is_active=m.organization.is_active,
            created_at=m.organization.created_at,
            user_role=m.role,
        )
        for m in memberships
    ]


@router.get(
    "/{org_id}",
    response_model=OrganizationRead,
    status_code=status.HTTP_200_OK,
    summary="Get Organization Details",
    description="Retrieves organization metadata. Access is restricted to members of the organization.",
)
def get_organization(
    org_id: uuid.UUID,
    tenant_ctx: TenantContext = Depends(require_role(RoleEnum.VIEWER)),
) -> OrganizationRead:
    return OrganizationRead(
        id=tenant_ctx.organization.id,
        name=tenant_ctx.organization.name,
        slug=tenant_ctx.organization.slug,
        is_active=tenant_ctx.organization.is_active,
        created_at=tenant_ctx.organization.created_at,
        user_role=tenant_ctx.role.value,
    )


@router.put(
    "/{org_id}",
    response_model=OrganizationRead,
    status_code=status.HTTP_200_OK,
    summary="Update Organization",
    description="Updates organization details. Requires ORG_ADMIN or ORG_OWNER role.",
)
def update_organization(
    org_id: uuid.UUID,
    req: OrganizationUpdate,
    tenant_ctx: TenantContext = Depends(require_role(RoleEnum.ORG_ADMIN)),
    db: Session = Depends(get_db),
) -> OrganizationRead:
    org = tenant_ctx.organization
    if req.name is not None:
        org.name = req.name
    if req.slug is not None and req.slug != org.slug:
        existing = db.query(Organization).filter(Organization.slug == req.slug).first()
        if existing and existing.id != org.id:
            raise ConflictException(f"Organization slug '{req.slug}' is already taken.")
        org.slug = req.slug
    if req.is_active is not None:
        org.is_active = req.is_active

    db.add(org)

    return OrganizationRead(
        id=org.id,
        name=org.name,
        slug=org.slug,
        is_active=org.is_active,
        created_at=org.created_at,
        user_role=tenant_ctx.role.value,
    )


@router.delete(
    "/{org_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Organization",
    description="Deactivates or deletes an organization. Requires ORG_OWNER role.",
)
def delete_organization(
    org_id: uuid.UUID,
    tenant_ctx: TenantContext = Depends(require_role(RoleEnum.ORG_OWNER)),
    db: Session = Depends(get_db),
) -> dict:
    org = tenant_ctx.organization
    org.is_active = False
    db.add(org)
    return {"message": f"Organization '{org.name}' has been deactivated.", "organization_id": str(org.id)}
