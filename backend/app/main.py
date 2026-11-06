"""
HealCloud Backend Application Entrypoint
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.core.exceptions import register_exception_handlers
from app.api.v1.router import api_v1_router
from app.db.session import check_db_health


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle event handler for application startup and shutdown.
    """
    # Startup
    setup_logging(log_level=settings.LOG_LEVEL)
    logger.info(
        f"Starting {settings.PROJECT_NAME} v{settings.VERSION} [{settings.ENVIRONMENT} mode]"
    )
    
    # Verify database connectivity
    try:
        db_check = check_db_health()
        logger.info(f"Database connection verified: {db_check}")
    except Exception as exc:
        logger.warning(f"Database not reachable during startup: {exc}")

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.PROJECT_NAME}")


def create_application() -> FastAPI:
    """
    Application factory initializing FastAPI with middleware, routers, and exception handlers.
    """
    app = FastAPI(
        title=f"{settings.PROJECT_NAME} Platform API",
        version=settings.VERSION,
        description=(
            "Intelligent Cloud Reliability & Self-Healing Platform API.\n\n"
            "Provides endpoints for active health monitoring, incident detection, "
            "rule-based root cause analysis, and policy-governed recovery simulation."
        ),
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url=f"{settings.API_V1_STR}/docs",
        redoc_url=f"{settings.API_V1_STR}/redoc",
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register centralized RFC 7807 exception handlers
    register_exception_handlers(app)

    # Mount API v1 routes
    app.include_router(api_v1_router, prefix=settings.API_V1_STR)

    @app.get(
        "/",
        tags=["Root"],
        summary="API Root",
        status_code=status.HTTP_200_OK,
    )
    def root():
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": f"Welcome to {settings.PROJECT_NAME} API",
                "version": settings.VERSION,
                "environment": settings.ENVIRONMENT,
                "documentation": f"{settings.API_V1_STR}/docs",
                "health": f"{settings.API_V1_STR}/health/live",
            },
        )

    return app


app = create_application()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
