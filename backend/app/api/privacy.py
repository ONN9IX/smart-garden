"""No publication/approval or physical erasure endpoint is exposed."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permissions import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.privacy import (
    AttestationInput,
    PaperConsentInput,
    RequestInput,
    RequestTransition,
)
from app.services import privacy

router = APIRouter(prefix="/privacy", tags=["Конфиденциальность"])
Database = Annotated[Session, Depends(get_db)]
Member = Annotated[
    User, Depends(require_role("DIRECTOR", "ADMIN", "TEACHER", "PARENT"))
]
Manager = Annotated[User, Depends(require_role("DIRECTOR", "ADMIN"))]
Director = Annotated[User, Depends(require_role("DIRECTOR"))]


@router.get("/public/provider")
def provider_documents(db: Database):
    return privacy.public_documents(db, None)


@router.get("/public/gardens/{organization_id}")
def garden_documents(organization_id: UUID, db: Database):
    return privacy.public_documents(db, organization_id)


@router.get("/me")
def my_privacy(user: Member, db: Database):
    return privacy.overview(db, user)


@router.post("/attestations", status_code=201)
def attest(payload: AttestationInput, user: Manager, db: Database):
    return privacy.attest(db, user, payload)


@router.get("/consents")
def consents(user: Member, db: Database):
    return privacy.list_consents(db, user)


@router.get("/subjects")
def subjects(user: Member, db: Database):
    return privacy.subject_choices(db, user)


@router.post("/consents", status_code=201)
def paper_consent(payload: PaperConsentInput, user: Manager, db: Database):
    return privacy.record_consent(db, user, payload)


@router.post("/consents/{consent_id}/withdraw")
def withdraw(consent_id: UUID, user: Member, db: Database):
    return privacy.withdraw_consent(db, user, consent_id)


@router.get("/requests")
def requests(user: Member, db: Database):
    return privacy.list_requests(db, user)


@router.get("/operator/requests")
def operator_requests(user: Director, db: Database):
    return privacy.list_requests(db, user, operator_queue=True)


@router.post("/requests", status_code=201)
def submit_request(payload: RequestInput, user: Member, db: Database):
    return privacy.create_request(db, user, payload)


@router.post("/operator/requests/{request_id}/status")
def change_request(
    request_id: UUID, payload: RequestTransition, user: Director, db: Database
):
    return privacy.transition_request(db, user, request_id, payload)
