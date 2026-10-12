import logging
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

logger = logging.getLogger("dependency_guardian.api")

from app.core.config import settings
from app.core.exceptions import AppException
from app.routers import (
    health,
    projects,
    dependencies,
    baselines,
    scans,
    incidents,
    repairs,
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Dependency Guardian Backend API for tracking dependency changes, incidents, validation, and repair workflows.",
    servers=[
        {"url": settings.API_PREFIX, "description": "API Base"},
        {"url": "/", "description": "Root Base"},
    ],
)

# CORS middleware
origins = settings.CORS_ORIGINS
if isinstance(origins, str):
    origins = [origins]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Standardized error handling matching OpenAPI contract
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error,
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "bad_request",
            "message": "Invalid request payload",
            "details": {"errors": exc.errors()},
        },
    )


@app.exception_handler(IntegrityError)
async def integrity_exception_handler(request: Request, exc: IntegrityError):
    logger.error(f"[Database Integrity Error] {exc}", exc_info=True)
    detail_msg = str(exc.orig) if hasattr(exc, "orig") and exc.orig else str(exc)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": "conflict_or_constraint_violation",
            "message": "Database constraint or foreign key violation occurred.",
            "details": {"detail": detail_msg},
        },
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error(f"[Database Error] {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "database_error",
            "message": "A database error occurred while processing the request.",
            "details": {"detail": str(exc)},
        },
    )


# Health router available at both root /health and /api/v1/health
app.include_router(health.router)
app.include_router(health.router, prefix=settings.API_PREFIX)

# Include API v1 routes
app.include_router(projects.router, prefix=settings.API_PREFIX)
app.include_router(dependencies.router, prefix=settings.API_PREFIX)
app.include_router(baselines.router, prefix=settings.API_PREFIX)
app.include_router(scans.router, prefix=settings.API_PREFIX)
app.include_router(incidents.router, prefix=settings.API_PREFIX)
app.include_router(repairs.router, prefix=settings.API_PREFIX)
