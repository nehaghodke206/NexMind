"""Main entry point for Dependency Guardian Sample API (v2)."""
from fastapi import FastAPI
from .api import orders_router, payments_router, products_router, users_router
from .core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Sample E-commerce Service API (v2) demonstrating breaking and non-breaking contract changes.",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    @app.get("/health", tags=["Health"], summary="Service health check")
    def health_check():
        return {
            "status": "ok",
            "version": settings.app_version,
            "service": "sample-api",
        }

    app.include_router(users_router, prefix=settings.api_prefix)
    app.include_router(products_router, prefix=settings.api_prefix)
    app.include_router(orders_router, prefix=settings.api_prefix)
    app.include_router(payments_router, prefix=settings.api_prefix)

    return app


app = create_app()
