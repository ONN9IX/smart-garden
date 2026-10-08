#!/usr/bin/env python3
"""Fail-closed import and OpenAPI smoke for the active FastAPI application."""

import importlib
import json
import pkgutil
import sys
from collections import Counter
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import app  # noqa: E402
from app.main import app as application  # noqa: E402


def main() -> None:
    imported = []
    for module in pkgutil.walk_packages(app.__path__, prefix="app."):
        importlib.import_module(module.name)
        imported.append(module.name)

    schema = application.openapi()
    if not schema.get("paths") or not schema.get("components", {}).get("schemas"):
        raise RuntimeError("OpenAPI is missing paths or schemas")

    operations = []
    for path, path_item in schema["paths"].items():
        for method in path_item:
            if method.lower() in {"get", "post", "put", "patch", "delete", "options", "head"}:
                operations.append((method.upper(), path))
    duplicates = [item for item, count in Counter(operations).items() if count > 1]
    if duplicates:
        raise RuntimeError(f"duplicate API operations: {duplicates}")

    route_pairs = [
        (method, route.path)
        for route in application.routes
        for method in getattr(route, "methods", set())
        if method not in {"HEAD", "OPTIONS"}
    ]
    duplicate_routes = [item for item, count in Counter(route_pairs).items() if count > 1]
    if duplicate_routes:
        raise RuntimeError(f"duplicate registered routes: {duplicate_routes}")

    with TestClient(application) as client:
        health = client.get("/api/v1/health")
    if health.status_code != 200 or health.json() != {"status": "ok"}:
        raise RuntimeError("health startup smoke failed")

    print(json.dumps({
        "imported_modules": len(imported),
        "openapi_operations": len(operations),
        "openapi_schemas": len(schema["components"]["schemas"]),
        "status": "ok",
    }, sort_keys=True))


if __name__ == "__main__":
    main()
