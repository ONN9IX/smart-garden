"""Stage 6 Track B router aggregation point."""

from fastapi import APIRouter

from app.api.teacher.parent import router as parent_router
from app.api.teacher.routes import router as teacher_router

router = APIRouter()
router.include_router(teacher_router)
router.include_router(parent_router)

__all__ = ["router"]
