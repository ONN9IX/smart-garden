"""Manual attendance management in the authenticated kindergarten."""

from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.api.error_responses import MANAGEMENT_ERRORS
from app.core.permissions import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.attendance import (
    AttendanceCreate,
    AttendanceDetail,
    AttendanceList,
    AttendancePatch,
)
from app.services import attendance

router = APIRouter(prefix="/attendance", tags=["Посещаемость"], responses=MANAGEMENT_ERRORS)
Manager = Annotated[User, Depends(require_role("DIRECTOR", "ADMIN"))]
Database = Annotated[Session, Depends(get_db)]


@router.get("", response_model=AttendanceList)
def list_attendance(user: Manager, db: Database, date: date,
                    group_id: UUID | None = None, child_id: UUID | None = None,
                    status: Literal["all", "present", "absent", "unknown"] = Query("all")) -> AttendanceList:
    return AttendanceList(items=attendance.list_day(db, user, date, group_id, status, child_id))


@router.post("", response_model=AttendanceDetail, status_code=201)
def save_attendance(payload: AttendanceCreate, user: Manager, db: Database, response: Response) -> AttendanceDetail:
    result, created = attendance.upsert(db, user, payload)
    if not created:
        response.status_code = 200
    return result


@router.get("/{record_id}", response_model=AttendanceDetail)
def get_attendance(record_id: UUID, user: Manager, db: Database) -> AttendanceDetail:
    return attendance.get(db, user, record_id)


@router.patch("/{record_id}", response_model=AttendanceDetail)
def patch_attendance(record_id: UUID, payload: AttendancePatch, user: Manager, db: Database) -> AttendanceDetail:
    return attendance.update(db, user, record_id, payload)
