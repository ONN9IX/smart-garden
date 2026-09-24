"""FastAPI application and safe errors for Stage 1.

Security: only fixed error strings leave the server; credential-bearing bodies and cookies are never logged.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.core.config import get_settings
from app.core.errors import (
    AppError,
    app_error_handler,
    error_response,
    validation_error_handler,
)

settings = get_settings()
logger = logging.getLogger("smart_garden.api")
app = FastAPI(title="Умный сад API", version="0.1.0")
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_middleware(
    CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=True,
    allow_methods=["GET", "POST"], allow_headers=["Content-Type"],
)


@app.middleware("http")
async def enforce_origin(request: Request, call_next):
    # CORS alone does not reject side-effecting cross-origin requests at the server.
    origin = request.headers.get("origin")
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and origin and origin not in settings.allowed_origins:
        return error_response(403, "FORBIDDEN")
    return await call_next(request)


@app.exception_handler(Exception)
async def unexpected_error(request: Request, error: Exception) -> JSONResponse:
    # Never log exception text: DB driver errors can include SQL params or credentials.
    logger.error("Unexpected %s at %s", type(error).__name__, request.url.path)
    return error_response(500, "INTERNAL_ERROR")


app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
