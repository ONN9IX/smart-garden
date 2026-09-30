"""Stage 6 shared router extension-point integration."""

import inspect

from fastapi import APIRouter

import app.main as main_module
from app.api.management import router as management_router
from app.api.teacher import router as teacher_router


def test_shared_router_extension_points_are_registered_without_placeholder_routes():
    assert isinstance(teacher_router, APIRouter)
    assert isinstance(management_router, APIRouter)
    assert teacher_router.routes == []
    assert management_router.routes == []

    source = inspect.getsource(main_module)
    assert 'app.include_router(teacher_router, prefix="/api/v1")' in source
    assert 'app.include_router(management_router, prefix="/api/v1")' in source

    spec = main_module.app.openapi()
    paths = set(spec["paths"])
    assert {
        "/api/v1/auth/me",
        "/api/v1/groups",
        "/api/v1/teacher-management/assignments",
    } <= paths
    assert {"get", "post"} <= spec["paths"]["/api/v1/teacher-management/assignments"].keys()
    assert not any(path.startswith("/api/v1/teacher/") for path in paths)
    assert not any(path.startswith("/api/v1/management/") for path in paths)
