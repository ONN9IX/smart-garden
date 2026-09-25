"""Server-side role and tenant guards for current and future business endpoints.

Security: organization IDs from a client never select an authenticated tenant.
"""

from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.core.errors import AppError
from app.models.user import User
from app.services.auth import current_user


def require_role(*roles: str) -> Callable:
    def dependency(user: Annotated[User, Depends(current_user)]) -> User:
        if user.role not in roles:
            raise AppError(403, "FORBIDDEN")
        return user

    return dependency


def require_tenant(user: User, resource_organization_id: UUID) -> None:
    if user.organization_id != resource_organization_id:
        # Hidden tenant resources get 404; never leak existence or payload.
        raise AppError(404, "NOT_FOUND")
