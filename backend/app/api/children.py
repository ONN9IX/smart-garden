"""Child API handlers; auth role and tenant checks remain server-side."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.permissions import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.child import (
    ChildCreate,
    ChildGuardianResponse,
    ChildList,
    ChildPatch,
    ChildResponse,
)
from app.schemas.relation import RelationCreate, RelationPatch
from app.services import children, relations

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


@router.post("/{child_id}/guardians", response_model=ChildGuardianResponse, status_code=201)
def link_guardian(child_id: UUID, payload: RelationCreate, response: Response, user: Manager, db: Database) -> ChildGuardianResponse:
    result, created = relations.link(db, user, child_id, payload.guardian_id, payload.relation_type)
    if not created:
        response.status_code = 200
    return result


@router.patch("/{child_id}/guardians/{guardian_id}", response_model=ChildGuardianResponse)
def update_link(child_id: UUID, guardian_id: UUID, payload: RelationPatch, user: Manager, db: Database) -> ChildGuardianResponse:
    return relations.update_relation(db, user, child_id, guardian_id, payload.relation_type)


@router.post("/{child_id}/guardians/{guardian_id}/archive", response_model=ChildGuardianResponse)
def archive_link(child_id: UUID, guardian_id: UUID, user: Manager, db: Database) -> ChildGuardianResponse:
    return relations.archive_relation(db, user, child_id, guardian_id)


@router.post("/{child_id}/guardians/{guardian_id}/restore", response_model=ChildGuardianResponse)
def restore_link(child_id: UUID, guardian_id: UUID, user: Manager, db: Database) -> ChildGuardianResponse:
    return relations.restore_relation(db, user, child_id, guardian_id)
