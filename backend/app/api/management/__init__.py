"""Stage 6 Track A router aggregation extension point."""

from fastapi import APIRouter

from app.api.management.cabinet import router as cabinet_router

router = APIRouter()
router.include_router(cabinet_router)

__all__ = ["router"]
