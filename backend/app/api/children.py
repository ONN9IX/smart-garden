"""Child API handlers; auth role and tenant checks remain server-side."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.permissions import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.child import ChildCreate, ChildList, ChildPatch, ChildResponse
from app.services import children

router = APIRouter(prefix="/children", tags=["Дети"])
Manager = Annotated[User, Depends(require_role("DIRECTOR", "ADMIN"))]
Database = Annotated[Session, Depends(get_db)]


@router.get("", response_model=ChildList)
def list_children(
    user: Manager, db: Database,
    status: Literal["active", "archived", "all"] = Query("active"),
    group_id: UUID | None = None, q: str | None = Query(None, max_length=100),
) -> ChildList:
    return ChildList(items=children.list_children(db, user, status, group_id, q))


@router.post("", response_model=ChildResponse, status_code=201)
def create_child(payload: ChildCreate, user: Manager, db: Database) -> ChildResponse:
    return children.create_child(db, user, payload)


@router.get("/{child_id}", response_model=ChildResponse)
def get_child(child_id: UUID, user: Manager, db: Database) -> ChildResponse:
    return children.detail(children.get_child(db, user, child_id))


@router.patch("/{child_id}", response_model=ChildResponse)
def update_child(child_id: UUID, payload: ChildPatch, user: Manager, db: Database) -> ChildResponse:
    return children.update_child(db, user, child_id, payload)


@router.post("/{child_id}/archive", response_model=ChildResponse)
def archive_child(child_id: UUID, user: Manager, db: Database) -> ChildResponse:
    return children.archive_child(db, user, child_id)


@router.post("/{child_id}/restore", response_model=ChildResponse)
def restore_child(child_id: UUID, user: Manager, db: Database) -> ChildResponse:
    return children.restore_child(db, user, child_id)
