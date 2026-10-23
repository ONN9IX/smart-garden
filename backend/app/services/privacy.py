"""Tenant-scoped privacy evidence and manual rights requests, never consent-by-login."""

import hashlib
import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, exists, or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.child import Child
from app.models.child_guardian import ChildGuardian
from app.models.employee import Employee
from app.models.guardian import Guardian
from app.models.privacy import (
    BasisAttestation,
    ConsentEvent,
    LegalDocument,
    PaperConsent,
    PrivacyRequest,
    ProcessingPurpose,
    RequestEvent,
)
from app.models.user import User
from app.schemas.privacy import (
    AttestationInput,
    PaperConsentInput,
    RequestInput,
    RequestTransition,
)
from app.services import audit
from app.services.privacy_catalog import (
    PurposeInput,
    document_is_effective,
    draft_inventory,
)
from app.services.tenant_locks import lock_tenant


def _manager(actor: User) -> None:
    if actor.role not in {"DIRECTOR", "ADMIN"}:
        raise AppError(403, "FORBIDDEN")


def _digest(payload) -> str:
    return hashlib.sha256(
        json.dumps(payload.model_dump(mode="json"), sort_keys=True).encode()
    ).hexdigest()


def _document(
    db: Session, document_id: UUID, organization_id: UUID
) -> LegalDocument | None:
    return db.scalar(
        select(LegalDocument).where(
            LegalDocument.id == document_id,
            LegalDocument.organization_id == organization_id,
        )
    )


def purpose_ready(db: Session, item: ProcessingPurpose) -> bool:
    try:
        PurposeInput.model_validate(item)
    except ValueError:
        return False
    document = _document(db, item.document_id, item.organization_id)
    if not item.enabled or not document or not document_is_effective(document):
        return False
    if document.document_type not in {"policy", "notice"}:
        return False
    if item.consent_required:
        consent = _document(db, item.consent_document_id, item.organization_id)
        if (
            not consent
            or consent.document_type != "paper_consent"
            or not document_is_effective(consent)
        ):
            return False
    return True


def _purpose(db: Session, actor: User, purpose_id: UUID) -> ProcessingPurpose:
    item = db.scalar(
        select(ProcessingPurpose).where(
            ProcessingPurpose.id == purpose_id,
            ProcessingPurpose.organization_id == actor.organization_id,
        )
    )
    if item is None:
        raise AppError(404, "NOT_FOUND")
    if not purpose_ready(db, item):
        raise AppError(409, "PRIVACY_NOT_APPROVED")
    return item


def document_view(item: LegalDocument) -> dict:
    return {
        "id": item.id,
        "organization_id": item.organization_id,
        "document_type": item.document_type,
        "version": item.version,
        "title": item.title,
        "operator": item.operator,
        "content": item.content,
        "content_hash": item.content_hash,
        "effective_at": item.effective_at,
    }


def public_documents(db: Session, organization_id: UUID | None) -> dict:
    documents = db.scalars(
        select(LegalDocument)
        .where(
            LegalDocument.organization_id == organization_id,
            LegalDocument.status == "published",
            LegalDocument.document_type.in_(("policy", "notice")),
        )
        .order_by(LegalDocument.created_at, LegalDocument.id)
    ).all()
    return {
        "documents": [
            document_view(item) for item in documents if document_is_effective(item)
        ],
        "real_pii_pilot": "NO-GO",
    }


def overview(db: Session, actor: User) -> dict:
    provider = public_documents(db, None)["documents"]
    garden = public_documents(db, actor.organization_id)["documents"]
    purposes = db.scalars(
        select(ProcessingPurpose)
        .where(
            ProcessingPurpose.organization_id == actor.organization_id,
        )
        .order_by(ProcessingPurpose.code, ProcessingPurpose.version)
    ).all()
    register = []
    for item in purposes:
        if (
            actor.role not in {"DIRECTOR", "ADMIN"}
            and actor.role not in item.access_roles
        ):
            continue
        register.append(
            {
                **{
                    field: getattr(item, field)
                    for field in (
                        "id",
                        "code",
                        "version",
                        "title",
                        "document_id",
                        "consent_document_id",
                        "subject_categories",
                        "data_categories",
                        "operations",
                        "access_roles",
                        "legal_basis",
                        "retention",
                        "processors",
                        "locations",
                        "consent_required",
                    )
                },
                "ready": purpose_ready(db, item),
            }
        )
    for item in draft_inventory():
        if item["code"] not in {p.code for p in purposes} and (
            actor.role in {"DIRECTOR", "ADMIN"} or actor.role in item["access_roles"]
        ):
            register.append(item)
    consent_documents = []
    for item in purposes:
        if (
            item.consent_document_id
            and purpose_ready(db, item)
            and (actor.role in {"DIRECTOR", "ADMIN"} or actor.role in item.access_roles)
        ):
            consent_documents.append(
                _document(db, item.consent_document_id, actor.organization_id)
            )
    return {
        "organization_id": actor.organization_id,
        "organization_name": actor.organization.name,
        "operator_configured": bool(garden),
        "documents": garden
        + provider
        + [document_view(d) for d in {d.id: d for d in consent_documents}.values()],
        "purposes": register,
        "real_pii_pilot": "NO-GO",
    }


def _profile(db: Session, actor: User, kind: str, profile_id: UUID):
    model = Guardian if kind == "guardian" else Employee
    item = db.scalar(
        select(model).where(
            model.id == profile_id, model.organization_id == actor.organization_id
        )
    )
    if item is None or item.status != "active":
        raise AppError(404, "NOT_FOUND")
    return item


def subject_choices(db: Session, actor: User) -> list[dict]:
    """Minimal selectors; never return contacts, birth dates or unrelated people."""
    manager = actor.role in {"DIRECTOR", "ADMIN"}
    query = select(User).where(
        User.organization_id == actor.organization_id, User.status == "active"
    )
    if not manager:
        query = query.where(User.id == actor.id)
    result = [
        {
            "subject_user_id": user.id,
            "child_id": None,
            "guardian_id": None,
            "label": "Мои данные" if user.id == actor.id else user.username,
        }
        for user in db.scalars(query).all()
    ]
    if manager or actor.role == "PARENT":
        links = (
            select(Child, Guardian)
            .join(ChildGuardian, ChildGuardian.child_id == Child.id)
            .join(
                Guardian,
                Guardian.id == ChildGuardian.guardian_id,
            )
            .where(
                Child.organization_id == actor.organization_id,
                Child.status == "active",
                ChildGuardian.organization_id == actor.organization_id,
                ChildGuardian.status == "active",
                Guardian.organization_id == actor.organization_id,
                Guardian.status == "active",
            )
        )
        if not manager:
            links = links.where(Guardian.user_id == actor.id)
        for child, guardian in db.execute(links).all():
            result.append(
                {
                    "subject_user_id": None,
                    "child_id": child.id,
                    "guardian_id": guardian.id,
                    "label": f"{child.last_name} {child.first_name} — представитель {guardian.last_name} {guardian.first_name}",
                }
            )
    return result


def attest(db: Session, actor: User, payload: AttestationInput) -> dict:
    _manager(actor)
    if payload.profile_type == "employee" and actor.role != "DIRECTOR":
        raise AppError(403, "FORBIDDEN")
    lock_tenant(db, actor.organization_id)
    purpose = _purpose(db, actor, payload.purpose_id)
    if purpose.code != "account_access" or "user" not in purpose.subject_categories:
        raise AppError(409, "PRIVACY_NOT_APPROVED")
    ids = list(dict.fromkeys(payload.profile_ids))
    # Validate every profile before recording anything.
    for profile_id in ids:
        _profile(db, actor, payload.profile_type, profile_id)
    for profile_id in ids:
        event = BasisAttestation(
            organization_id=actor.organization_id,
            actor_user_id=actor.id,
            profile_type=payload.profile_type,
            profile_id=profile_id,
            purpose_id=purpose.id,
        )
        db.add(event)
        db.flush()
        audit.write(db, actor, "privacy.attest", "privacy_attestation", event.id)
    db.commit()
    return {"recorded": len(ids), "is_subject_consent": False}


def require_invitation_basis(
    db: Session, actor: User, kind: str, profile_id: UUID
) -> BasisAttestation:
    _manager(actor)
    lock_tenant(db, actor.organization_id)
    events = db.scalars(
        select(BasisAttestation)
        .where(
            BasisAttestation.organization_id == actor.organization_id,
            BasisAttestation.profile_type == kind,
            BasisAttestation.profile_id == profile_id,
        )
        .order_by(BasisAttestation.created_at.desc(), BasisAttestation.id.desc())
    ).all()
    for event in events:
        purpose = db.scalar(
            select(ProcessingPurpose).where(
                ProcessingPurpose.id == event.purpose_id,
                ProcessingPurpose.organization_id == actor.organization_id,
            )
        )
        if purpose and purpose.code == "account_access" and purpose_ready(db, purpose):
            return event
    raise AppError(409, "PRIVACY_BASIS_REQUIRED")


def _parent_child(
    db: Session, actor: User, child_id: UUID, guardian_id: UUID | None = None
) -> None:
    query = (
        select(ChildGuardian.id)
        .join(Guardian, Guardian.id == ChildGuardian.guardian_id)
        .join(
            Child,
            Child.id == ChildGuardian.child_id,
        )
        .where(
            ChildGuardian.organization_id == actor.organization_id,
            ChildGuardian.child_id == child_id,
            ChildGuardian.status == "active",
            Guardian.organization_id == actor.organization_id,
            Guardian.user_id == actor.id,
            Guardian.status == "active",
            Child.organization_id == actor.organization_id,
            Child.status == "active",
        )
    )
    if guardian_id is not None:
        query = query.where(Guardian.id == guardian_id)
    if actor.role != "PARENT" or db.scalar(query) is None:
        raise AppError(404, "NOT_FOUND")


def _visible_consent(db: Session, actor: User, item: PaperConsent) -> bool:
    if item.organization_id != actor.organization_id:
        return False
    if actor.role in {"DIRECTOR", "ADMIN"}:
        return True
    if item.subject_user_id == actor.id:
        return True
    if item.child_id and actor.role == "PARENT":
        try:
            _parent_child(db, actor, item.child_id, item.guardian_id)
            return True
        except AppError:
            return False
    return False


def consent_view(db: Session, actor: User, item: PaperConsent) -> dict:
    document = _document(db, item.document_id, actor.organization_id)
    purpose = db.scalar(
        select(ProcessingPurpose).where(
            ProcessingPurpose.id == item.purpose_id,
            ProcessingPurpose.organization_id == actor.organization_id,
        )
    )
    events = db.scalars(
        select(ConsentEvent)
        .where(
            ConsentEvent.organization_id == actor.organization_id,
            ConsentEvent.consent_id == item.id,
        )
        .order_by(ConsentEvent.created_at, ConsentEvent.id)
    ).all()
    withdrawn = any(event.action == "withdrawn" for event in events)
    return {
        "id": item.id,
        "purpose_id": item.purpose_id,
        "purpose_title": purpose.title,
        "subject_user_id": item.subject_user_id,
        "child_id": item.child_id,
        "guardian_id": item.guardian_id,
        "document_id": item.document_id,
        "document_type": document.document_type,
        "document_version": document.version,
        "document_hash": document.content_hash,
        "document": document_view(document),
        "received_on": item.received_on,
        "recorded_by": item.actor_user_id,
        "status": "withdrawn" if withdrawn else "recorded",
        "current_version": purpose_ready(db, purpose),
        "history": [
            {"action": e.action, "at": e.created_at, "actor_user_id": e.actor_user_id}
            for e in events
        ],
    }


def list_consents(db: Session, actor: User) -> list[dict]:
    query = select(PaperConsent).where(
        PaperConsent.organization_id == actor.organization_id
    )
    if actor.role not in {"DIRECTOR", "ADMIN"}:
        # Restrict in SQL before loading data; relation checks also revalidated below.
        own_child = exists(
            select(ChildGuardian.id)
            .join(Guardian, Guardian.id == ChildGuardian.guardian_id)
            .where(
                ChildGuardian.organization_id == actor.organization_id,
                ChildGuardian.child_id == PaperConsent.child_id,
                ChildGuardian.guardian_id == PaperConsent.guardian_id,
                ChildGuardian.status == "active",
                Guardian.organization_id == actor.organization_id,
                Guardian.user_id == actor.id,
                Guardian.status == "active",
            )
        )
        query = query.where(
            or_(
                PaperConsent.subject_user_id == actor.id,
                and_(PaperConsent.child_id.is_not(None), own_child)
                if actor.role == "PARENT"
                else False,
            )
        )
    return [
        consent_view(db, actor, item)
        for item in db.scalars(query.order_by(PaperConsent.created_at.desc())).all()
        if _visible_consent(db, actor, item)
    ]


def record_consent(db: Session, actor: User, payload: PaperConsentInput) -> dict:
    _manager(actor)
    lock_tenant(db, actor.organization_id)
    purpose = _purpose(db, actor, payload.purpose_id)
    if (
        not purpose.consent_required
        or purpose.consent_document_id != payload.document_id
    ):
        raise AppError(409, "PRIVACY_NOT_APPROVED")
    if payload.received_on > datetime.now(UTC).date():
        raise AppError(400, "VALIDATION_ERROR")
    document = _document(db, payload.document_id, actor.organization_id)
    if payload.received_on < max(
        document.effective_at.date(), document.approved_at.date()
    ):
        raise AppError(400, "VALIDATION_ERROR", "received_on")
    if payload.subject_user_id:
        user = db.scalar(
            select(User).where(
                User.id == payload.subject_user_id,
                User.organization_id == actor.organization_id,
            )
        )
        if (
            not user
            or user.status != "active"
            or "user" not in purpose.subject_categories
        ):
            raise AppError(404, "NOT_FOUND")
    else:
        child = db.scalar(
            select(Child.id).where(
                Child.id == payload.child_id,
                Child.organization_id == actor.organization_id,
                Child.status == "active",
            )
        )
        relation = db.scalar(
            select(ChildGuardian.id)
            .join(Guardian, Guardian.id == ChildGuardian.guardian_id)
            .where(
                ChildGuardian.organization_id == actor.organization_id,
                ChildGuardian.child_id == payload.child_id,
                ChildGuardian.guardian_id == payload.guardian_id,
                ChildGuardian.status == "active",
                Guardian.organization_id == actor.organization_id,
                Guardian.status == "active",
            )
        )
        if not child or not relation or "child" not in purpose.subject_categories:
            raise AppError(404, "NOT_FOUND")
    previous = db.scalar(
        select(PaperConsent).where(
            PaperConsent.organization_id == actor.organization_id,
            PaperConsent.actor_user_id == actor.id,
            PaperConsent.idempotency_key == payload.idempotency_key,
        )
    )
    if previous:
        if previous.request_digest != _digest(payload):
            raise AppError(409, "IDEMPOTENCY_KEY_REUSED")
        return consent_view(db, actor, previous)
    latest_withdrawal = db.scalar(
        select(ConsentEvent.created_at)
        .join(PaperConsent, PaperConsent.id == ConsentEvent.consent_id)
        .join(
            ProcessingPurpose,
            ProcessingPurpose.id == PaperConsent.purpose_id,
        )
        .where(
            ConsentEvent.organization_id == actor.organization_id,
            PaperConsent.organization_id == actor.organization_id,
            ProcessingPurpose.organization_id == actor.organization_id,
            ProcessingPurpose.code == purpose.code,
            PaperConsent.subject_user_id == payload.subject_user_id,
            PaperConsent.child_id == payload.child_id,
            PaperConsent.guardian_id == payload.guardian_id,
            ConsentEvent.action == "withdrawn",
        )
        .order_by(ConsentEvent.created_at.desc())
        .limit(1)
    )
    if latest_withdrawal and payload.received_on <= latest_withdrawal.date():
        raise AppError(409, "PRIVACY_NEW_ORIGINAL_REQUIRED")
    existing = db.scalar(
        select(PaperConsent.id).where(
            PaperConsent.organization_id == actor.organization_id,
            PaperConsent.purpose_id == purpose.id,
            PaperConsent.subject_user_id == payload.subject_user_id,
            PaperConsent.child_id == payload.child_id,
            PaperConsent.guardian_id == payload.guardian_id,
            ~exists(
                select(ConsentEvent.id).where(
                    ConsentEvent.organization_id == actor.organization_id,
                    ConsentEvent.consent_id == PaperConsent.id,
                    ConsentEvent.action == "withdrawn",
                )
            ),
        )
    )
    if existing:
        raise AppError(409, "PRIVACY_ALREADY_RECORDED")
    item = PaperConsent(
        organization_id=actor.organization_id,
        actor_user_id=actor.id,
        request_digest=_digest(payload),
        **payload.model_dump(
            exclude={"original_held_confirmed", "authority_confirmed"}
        ),
    )
    db.add(item)
    db.flush()
    db.add(
        ConsentEvent(
            organization_id=actor.organization_id,
            consent_id=item.id,
            actor_user_id=actor.id,
            action="recorded",
        )
    )
    audit.write(db, actor, "privacy.consent.record", "privacy_consent", item.id)
    db.commit()
    return consent_view(db, actor, item)


def withdraw_consent(db: Session, actor: User, consent_id: UUID) -> dict:
    lock_tenant(db, actor.organization_id)
    item = db.scalar(
        select(PaperConsent)
        .where(
            PaperConsent.id == consent_id,
            PaperConsent.organization_id == actor.organization_id,
        )
        .with_for_update()
    )
    if not item or not _visible_consent(db, actor, item):
        raise AppError(404, "NOT_FOUND")
    purpose = db.scalar(
        select(ProcessingPurpose).where(
            ProcessingPurpose.organization_id == actor.organization_id,
            ProcessingPurpose.id == item.purpose_id,
        )
    )
    # Withdrawing a purpose also covers its previous versions for the SAME subject
    # and verified representative; another representative's evidence stays private.
    related = db.scalars(
        select(PaperConsent)
        .join(ProcessingPurpose, ProcessingPurpose.id == PaperConsent.purpose_id)
        .where(
            PaperConsent.organization_id == actor.organization_id,
            ProcessingPurpose.organization_id == actor.organization_id,
            ProcessingPurpose.code == purpose.code,
            PaperConsent.subject_user_id == item.subject_user_id,
            PaperConsent.child_id == item.child_id,
            PaperConsent.guardian_id == item.guardian_id,
        )
    ).all()
    for consent in related:
        previous = db.scalar(
            select(ConsentEvent.id).where(
                ConsentEvent.organization_id == actor.organization_id,
                ConsentEvent.consent_id == consent.id,
                ConsentEvent.action == "withdrawn",
            )
        )
        if not previous:
            db.add(
                ConsentEvent(
                    organization_id=actor.organization_id,
                    consent_id=consent.id,
                    actor_user_id=actor.id,
                    action="withdrawn",
                )
            )
            audit.write(
                db, actor, "privacy.consent.withdraw", "privacy_consent", consent.id
            )
    db.commit()
    return consent_view(db, actor, item)


def request_view(db: Session, actor: User, item: PrivacyRequest) -> dict:
    history = db.scalars(
        select(RequestEvent)
        .where(
            RequestEvent.organization_id == actor.organization_id,
            RequestEvent.request_id == item.id,
        )
        .order_by(RequestEvent.created_at, RequestEvent.id)
    ).all()
    return {
        "id": item.id,
        "organization_id": item.organization_id,
        "requester_user_id": item.requester_user_id,
        "child_id": item.child_id,
        "kind": item.kind,
        "status": item.status,
        "due_at": item.due_at,
        "needs_deadline": item.due_at is None
        and item.status not in {"completed", "declined"},
        "overdue": bool(
            item.due_at
            and item.due_at < datetime.now(UTC)
            and item.status not in {"completed", "declined"}
        ),
        "created_at": item.created_at,
        "history": [
            {
                "status": e.status,
                "at": e.created_at,
                "actor_user_id": e.actor_user_id,
                "decision_code": e.decision_code,
                "due_at": e.due_at,
            }
            for e in history
        ],
    }


def list_requests(
    db: Session, actor: User, *, operator_queue: bool = False
) -> list[dict]:
    if operator_queue and actor.role != "DIRECTOR":
        raise AppError(403, "FORBIDDEN")
    query = select(PrivacyRequest).where(
        PrivacyRequest.organization_id == actor.organization_id
    )
    if not operator_queue:
        query = query.where(PrivacyRequest.requester_user_id == actor.id)
    items = db.scalars(query.order_by(PrivacyRequest.created_at.desc())).all()
    result = []
    for item in items:
        if item.child_id and not operator_queue:
            try:
                _parent_child(db, actor, item.child_id)
            except AppError:
                continue
        result.append(request_view(db, actor, item))
    return result


def create_request(db: Session, actor: User, payload: RequestInput) -> dict:
    if payload.child_id:
        _parent_child(db, actor, payload.child_id)
    lock_tenant(db, actor.organization_id)
    previous = db.scalar(
        select(PrivacyRequest).where(
            PrivacyRequest.organization_id == actor.organization_id,
            PrivacyRequest.requester_user_id == actor.id,
            PrivacyRequest.idempotency_key == payload.idempotency_key,
        )
    )
    if previous:
        if previous.request_digest != _digest(payload):
            raise AppError(409, "IDEMPOTENCY_KEY_REUSED")
        return request_view(db, actor, previous)
    item = PrivacyRequest(
        organization_id=actor.organization_id,
        requester_user_id=actor.id,
        request_digest=_digest(payload),
        **payload.model_dump(),
    )
    db.add(item)
    db.flush()
    db.add(
        RequestEvent(
            organization_id=actor.organization_id,
            request_id=item.id,
            actor_user_id=actor.id,
            status="submitted",
        )
    )
    audit.write(db, actor, "privacy.request.create", "privacy_request", item.id)
    db.commit()
    return request_view(db, actor, item)


def transition_request(
    db: Session, actor: User, request_id: UUID, payload: RequestTransition
) -> dict:
    if actor.role != "DIRECTOR":
        raise AppError(403, "FORBIDDEN")
    lock_tenant(db, actor.organization_id)
    item = db.scalar(
        select(PrivacyRequest)
        .where(
            PrivacyRequest.id == request_id,
            PrivacyRequest.organization_id == actor.organization_id,
        )
        .with_for_update()
    )
    if not item:
        raise AppError(404, "NOT_FOUND")
    allowed = {
        "submitted": {"verifying"},
        "verifying": {"in_review", "declined"},
        "in_review": {"completed", "declined"},
    }
    if item.status != payload.expected_status or payload.status not in allowed.get(
        item.status, set()
    ):
        raise AppError(409, "PRIVACY_REQUEST_STATE")
    if payload.due_at and payload.due_at.tzinfo is None:
        raise AppError(400, "VALIDATION_ERROR")
    if payload.status in {"completed", "declined"} and (
        not payload.outcome_confirmed or not payload.decision_code
    ):
        raise AppError(400, "VALIDATION_ERROR")
    if payload.status == "completed" and payload.decision_code != "fulfilled_offline":
        raise AppError(400, "VALIDATION_ERROR")
    if payload.status == "declined" and payload.decision_code == "fulfilled_offline":
        raise AppError(400, "VALIDATION_ERROR")
    if payload.status not in {"completed", "declined"} and not (
        payload.due_at or item.due_at
    ):
        raise AppError(400, "VALIDATION_ERROR", "due_at")
    item.status = payload.status
    if payload.due_at:
        item.due_at = payload.due_at
    db.add(
        RequestEvent(
            organization_id=actor.organization_id,
            request_id=item.id,
            actor_user_id=actor.id,
            status=item.status,
            decision_code=payload.decision_code,
            due_at=item.due_at,
        )
    )
    audit.write(db, actor, "privacy.request.status", "privacy_request", item.id)
    db.commit()
    return request_view(db, actor, item)
