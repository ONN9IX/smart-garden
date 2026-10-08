#!/usr/bin/env python3
"""Emit a sanitized, machine-readable runtime/dependency report."""

import importlib.metadata
import json
import os
import platform
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def package(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "unavailable"


def command(*args: str) -> str:
    try:
        return subprocess.run(args, check=True, capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def postgresql_version() -> str:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        import psycopg
        with psycopg.connect(database_url.replace("postgresql+psycopg://", "postgresql://")) as connection:
            return str(connection.execute("SHOW server_version").fetchone()[0])
    return command("psql", "--version")


def frontend_versions() -> dict[str, str]:
    lock = json.loads((ROOT / "frontend" / "package-lock.json").read_text())
    packages = lock["packages"]
    return {
        name: packages.get(f"node_modules/{path}", {}).get("version", "unavailable")
        for name, path in {
            "next": "next", "react": "react", "typescript": "typescript",
            "playwright": "@playwright/test",
        }.items()
    }


report = {
    "lane": os.getenv("COMPATIBILITY_LANE", "production-pinned"),
    "python": platform.python_version(),
    "node": command("node", "--version").removeprefix("v"),
    "postgresql": postgresql_version(),
    "backend": {
        name: package(distribution)
        for name, distribution in {
            "fastapi": "fastapi", "sqlalchemy": "SQLAlchemy", "alembic": "alembic",
            "psycopg": "psycopg",
        }.items()
    },
    "frontend": frontend_versions(),
}
print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
