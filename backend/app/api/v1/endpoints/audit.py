"""
Immutable Audit Trail API Endpoints (Tenant-Scoped)
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.deps import get_tenant_context, TenantContext
from app.db.session import get_db
from app.models.audit import AuditLog
from app.schemas.audit import AuditLogResponse

router = APIRouter(
    prefix="/organizations/{org_id}/audit-logs",
    tags=["Audit & Compliance"],
)


@router.get("", response_model=List[AuditLogResponse])
def list_audit_logs(
    org_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    action: Optional[str] = Query(None),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    query = db.query(AuditLog).filter(AuditLog.organization_id == org_id)
    if action:
        query = query.filter(AuditLog.action == action)

    logs = query.order_by(desc(AuditLog.created_at)).limit(limit).all()
    return logs

