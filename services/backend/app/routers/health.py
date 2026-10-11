from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Check backend health")
def get_health() -> dict:
    return {"status": "ok", "version": settings.VERSION}
