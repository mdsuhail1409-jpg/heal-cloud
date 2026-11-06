"""
Workspace Management API Endpoints (Tenant-Scoped)
"""

import re
import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, EntityNotFoundException
from app.core.deps import (
    require_role,
    TenantContext,
)
from app.db.session import get_db
from app.models.organization import Workspace
from app.models.membership import RoleEnum
from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceUpdate,
    WorkspaceRead,
)

router = APIRouter(prefix="/organizations/{org_id}/workspaces", tags=["Workspaces"])


def _slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", slug)


@router.get(
    "",
    response_model=List[WorkspaceRead],
    status_code=status.HTTP_200_OK,
    summary="List Organization Workspaces",
    description="Returns all workspaces configured within the organization. Accessible to all org members.",
)
def list_workspaces(
    org_id: uuid.UUID,
    tenant_ctx: TenantContext = Depends(require_role(RoleEnum.VIEWER)),
    db: Session = Depends(get_db),
) -> List[WorkspaceRead]:
    workspaces = (
        db.query(Workspace)
        .filter(Workspace.organization_id == org_id)
        .order_by(Workspace.created_at.asc())
        .all()
    )
    return [WorkspaceRead.model_validate(w) for w in workspaces]


@router.post(
    "",
    response_model=WorkspaceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Workspace",
    description="Creates a new workspace within the organization. Requires ORG_ADMIN or ORG_OWNER role.",
)
def create_workspace(
    org_id: uuid.UUID,
    req: WorkspaceCreate,
    tenant_ctx: TenantContext = Depends(require_role(RoleEnum.ORG_ADMIN)),
    db: Session = Depends(get_db),
) -> WorkspaceRead:
    slug = req.slug or _slugify(req.name)
    existing = (
        db.query(Workspace)
        .filter(Workspace.organization_id == org_id, Workspace.slug == slug)
        .first()
    )
    if existing:
        raise ConflictException(
            f"A workspace with slug '{slug}' already exists in this organization.",
            details={"slug": slug, "organization_id": str(org_id)},
        )

    ws = Workspace(
        organization_id=org_id,
        name=req.name,
        slug=slug,
        description=req.description,
    )
    db.add(ws)
    db.flush()

    return WorkspaceRead.model_validate(ws)


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceRead,
    status_code=status.HTTP_200_OK,
    summary="Get Workspace",
    description="Fetches a workspace by ID. Strictly scoped to the specified organization to prevent cross-tenant access.",
)
def get_workspace(
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
    tenant_ctx: TenantContext = Depends(require_role(RoleEnum.VIEWER)),
    db: Session = Depends(get_db),
) -> WorkspaceRead:
    ws = (
        db.query(Workspace)
        .filter(
            Workspace.id == workspace_id,
            Workspace.organization_id == org_id,
        )
        .first()
    )
    if not ws:
        raise EntityNotFoundException("Workspace", workspace_id)

    return WorkspaceRead.model_validate(ws)


@router.put(
    "/{workspace_id}",
    response_model=WorkspaceRead,
    status_code=status.HTTP_200_OK,
    summary="Update Workspace",
    description="Updates workspace metadata. Requires ORG_ADMIN or ORG_OWNER role.",
)
def update_workspace(
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
    req: WorkspaceUpdate,
    tenant_ctx: TenantContext = Depends(require_role(RoleEnum.ORG_ADMIN)),
    db: Session = Depends(get_db),
) -> WorkspaceRead:
    ws = (
        db.query(Workspace)
        .filter(
            Workspace.id == workspace_id,
            Workspace.organization_id == org_id,
        )
        .first()
    )
    if not ws:
        raise EntityNotFoundException("Workspace", workspace_id)

    if req.name is not None:
        ws.name = req.name
    if req.description is not None:
        ws.description = req.description

    db.add(ws)
    return WorkspaceRead.model_validate(ws)


@router.delete(
    "/{workspace_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Workspace",
    description="Deletes a workspace. Requires ORG_OWNER role.",
)
def delete_workspace(
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
    tenant_ctx: TenantContext = Depends(require_role(RoleEnum.ORG_OWNER)),
    db: Session = Depends(get_db),
) -> dict:
    ws = (
        db.query(Workspace)
        .filter(
            Workspace.id == workspace_id,
            Workspace.organization_id == org_id,
        )
        .first()
    )
    if not ws:
        raise EntityNotFoundException("Workspace", workspace_id)

    db.delete(ws)
    return {
        "message": f"Workspace '{ws.name}' deleted successfully.",
        "workspace_id": str(workspace_id),
    }

