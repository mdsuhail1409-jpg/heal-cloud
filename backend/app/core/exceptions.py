"""
Centralised Exception Hierarchy and RFC 7807 Problem Details Handlers
"""

from typing import Any, Dict, Optional
from datetime import datetime, timezone
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.logging import logger


class HealCloudException(Exception):
    """Base exception class for all application-specific errors."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        title: str = "Internal Server Error",
        error_type: str = "https://errors.healcloud.io/internal_error",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.title = title
        self.error_type = error_type
        self.details = details or {}


class EntityNotFoundException(HealCloudException):
    """Resource not found error."""

    def __init__(self, entity_name: str, identifier: Any):
        super().__init__(
            message=f"{entity_name} with identifier '{identifier}' was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
            title="Entity Not Found",
            error_type="https://errors.healcloud.io/not_found",
            details={"entity": entity_name, "identifier": str(identifier)},
        )


class ValidationException(HealCloudException):
    """Business rule validation failure."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            title="Validation Error",
            error_type="https://errors.healcloud.io/validation_error",
            details=details,
        )


class DatabaseConnectionException(HealCloudException):
    """Database connectivity failure."""

    def __init__(self, message: str = "Database service is currently unreachable."):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            title="Database Unavailable",
            error_type="https://errors.healcloud.io/database_unavailable",
        )


class UnauthorizedException(HealCloudException):
    """Authentication required or invalid."""

    def __init__(self, message: str = "Authentication credentials are invalid or missing."):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Unauthorized",
            error_type="https://errors.healcloud.io/unauthorized",
        )


class ForbiddenException(HealCloudException):
    """Insufficient privileges."""

    def __init__(self, message: str = "You do not have permission to perform this action."):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            title="Forbidden",
            error_type="https://errors.healcloud.io/forbidden",
        )


class ConflictException(HealCloudException):
    """Resource conflict (e.g., duplicate slug or unique constraint)."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            title="Resource Conflict",
            error_type="https://errors.healcloud.io/conflict",
            details=details,
        )


def _build_problem_details(
    status_code: int,
    title: str,
    detail: str,
    error_type: str,
    instance: str,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload = {
        "type": error_type,
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": instance,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        payload["details"] = extra
    return payload


async def healcloud_exception_handler(request: Request, exc: HealCloudException) -> JSONResponse:
    logger.warning(
        f"Handled application exception: {exc.title} | {exc.message} on {request.url.path}"
    )
    problem = _build_problem_details(
        status_code=exc.status_code,
        title=exc.title,
        detail=exc.message,
        error_type=exc.error_type,
        instance=request.url.path,
        extra=exc.details,
    )
    return JSONResponse(status_code=exc.status_code, content=problem)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = []
    for err in exc.errors():
        field_path = ".".join(str(loc) for loc in err.get("loc", []))
        errors.append({
            "field": field_path,
            "message": err.get("msg"),
            "type": err.get("type"),
        })

    problem = _build_problem_details(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        title="Request Validation Failed",
        detail="The request body or parameters failed validation schema checks.",
        error_type="https://errors.healcloud.io/validation_error",
        instance=request.url.path,
        extra={"validation_errors": errors},
    )
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=problem)


async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    problem = _build_problem_details(
        status_code=exc.status_code,
        title="HTTP Error",
        detail=str(exc.detail),
        error_type="https://errors.healcloud.io/http_error",
        instance=request.url.path,
    )
    return JSONResponse(status_code=exc.status_code, content=problem)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"Unhandled system exception on {request.url.path}: {exc}", exc_info=True)
    problem = _build_problem_details(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        title="Internal Server Error",
        detail="An unexpected internal server error occurred. Our reliability engineers have been notified.",
        error_type="https://errors.healcloud.io/internal_error",
        instance=request.url.path,
    )
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=problem)


def register_exception_handlers(app: FastAPI) -> None:
    """Register all centralized RFC 7807 problem detail exception handlers."""
    app.add_exception_handler(HealCloudException, healcloud_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, starlette_http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
