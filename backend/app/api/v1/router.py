"""
API v1 Router Aggregator
"""

from fastapi import APIRouter
from app.api.v1.endpoints import (
    health,
    auth,
    organizations,
    workspaces,
    memberships,
    services,
    incidents,
    recovery,
    audit,
    metrics,
)

api_v1_router = APIRouter()

# Register endpoint modules
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(organizations.router)
api_v1_router.include_router(workspaces.router)
api_v1_router.include_router(memberships.router)
api_v1_router.include_router(services.router)
api_v1_router.include_router(incidents.router)
api_v1_router.include_router(recovery.router)
api_v1_router.include_router(audit.router)
api_v1_router.include_router(metrics.router)
