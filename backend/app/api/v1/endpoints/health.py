"""
Health, Readiness and Metadata Endpoints
"""

from datetime import datetime, timezone
from fastapi import APIRouter, status
from pydantic import BaseModel

from app.core.config import settings
from app.db.session import check_db_health

router = APIRouter(prefix="/health", tags=["Health & Readiness"])


class LivenessResponse(BaseModel):
    status: str
    timestamp: str


class ReadinessResponse(BaseModel):
    status: str
    timestamp: str
    database: dict


class AppInfoResponse(BaseModel):
    project_name: str
    version: str
    environment: str
    debug: bool
    api_prefix: str
    timestamp: str


@router.get(
    "/live",
    response_model=LivenessResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness Probe",
    description="Returns 200 OK if the application process is running and accepting HTTP requests.",
)
def liveness_probe() -> LivenessResponse:
    return LivenessResponse(
        status="alive",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness Probe",
    description="Validates downstream dependencies (database connection). Returns 503 if database is unreachable.",
)
def readiness_probe() -> ReadinessResponse:
    db_status = check_db_health()
    return ReadinessResponse(
        status="ready",
        timestamp=datetime.now(timezone.utc).isoformat(),
        database=db_status,
    )


@router.get(
    "/info",
    response_model=AppInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Application Information",
    description="Provides application metadata, versioning, and environment configuration.",
)
def app_info() -> AppInfoResponse:
    return AppInfoResponse(
        project_name=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        debug=settings.DEBUG,
        api_prefix=settings.API_V1_STR,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

