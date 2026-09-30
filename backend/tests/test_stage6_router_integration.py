"""Stage 6 shared router extension-point integration."""

import inspect

from fastapi import APIRouter

import app.main as main_module
from app.api.management import router as management_router
from app.api.teacher import router as teacher_router


def test_shared_router_extension_points_are_registered_without_main_rewrites():
    assert isinstance(teacher_router, APIRouter)
    assert isinstance(management_router, APIRouter)

    source = inspect.getsource(main_module)
    assert 'app.include_router(teacher_router, prefix="/api/v1")' in source
    assert 'app.include_router(management_router, prefix="/api/v1")' in source

    spec = main_module.app.openapi()
    paths = set(spec["paths"])
    assert {
        "/api/v1/auth/me",
        "/api/v1/groups",
        "/api/v1/teacher-management/assignments",
        "/api/v1/management/today",
        "/api/v1/management/settings",
        "/api/v1/teacher-management/teachers",
        "/api/v1/teacher-management/schedule",
    } <= paths
    assert {"get", "post"} <= spec["paths"]["/api/v1/teacher-management/assignments"].keys()
    assert {"get"} <= spec["paths"]["/api/v1/management/today"].keys()
    assert {"get", "patch"} <= spec["paths"]["/api/v1/management/settings"].keys()
