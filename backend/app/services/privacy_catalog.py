"""Reviewed, versioned legal catalog. Publication has no tenant HTTP endpoint."""

import hashlib
import re
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

PURPOSE_CODES = {
    "account_access",
    "child_roster",
    "family_contacts",
    "staff",
    "attendance",
    "schedule",
    "communications",
    "announcements",
    "tasks",
    "notifications",
    "security_audit",
    "rights_requests",
}
SUBJECTS = {"user", "child"}
ROLES = {"DIRECTOR", "ADMIN", "TEACHER", "PARENT"}
UNRESOLVED = re.compile(
    r"\[[^\]\n]*(?:ОПЕРАТОР|РЕКВИЗИТ|УТВЕРЖ|ДАТА|CONTACT|OPERATOR|TODO)[^\]\n]*\]|\b(?:TODO|TBD|TBC)\b",
    re.IGNORECASE,
)


def fingerprint(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


# Technical inventory only. None of these rows is a legal ground or permission.
_INVENTORY = [
    (
        "account_access",
        "Доступ к кабинету и приглашения",
        ["user"],
        ["Логин, email приглашения, роль и статус аккаунта"],
        ["DIRECTOR", "ADMIN", "TEACHER", "PARENT"],
    ),
    (
        "child_roster",
        "Состав групп",
        ["child"],
        ["ФИО, дата рождения, группа и статус ребёнка"],
        ["DIRECTOR", "ADMIN", "TEACHER", "PARENT"],
    ),
    (
        "family_contacts",
        "Контакты представителей и связи с детьми",
        ["user", "child"],
        ["ФИО представителя, email/телефон, связь с ребёнком"],
        ["DIRECTOR", "ADMIN", "TEACHER", "PARENT"],
    ),
    (
        "staff",
        "Сотрудники и назначения",
        ["user"],
        ["ФИО, должность, рабочие контакты, назначенные группы"],
        ["DIRECTOR", "ADMIN", "TEACHER"],
    ),
    (
        "attendance",
        "Учёт посещаемости",
        ["child"],
        ["Ребёнок, группа, дата, статус, время прихода и ухода, автор"],
        ["DIRECTOR", "ADMIN", "TEACHER", "PARENT"],
    ),
    (
        "schedule",
        "Расписание",
        ["user", "child"],
        ["Группа, день недели, время, название занятия"],
        ["DIRECTOR", "ADMIN", "TEACHER", "PARENT"],
    ),
    (
        "communications",
        "Организационная переписка",
        ["user", "child"],
        ["Участники, группа, содержание сообщения, время, прочтение"],
        ["DIRECTOR", "ADMIN", "TEACHER", "PARENT"],
    ),
    (
        "announcements",
        "Объявления",
        ["user"],
        ["Автор, аудитория, содержание, прочтение"],
        ["DIRECTOR", "ADMIN", "TEACHER", "PARENT"],
    ),
    (
        "tasks",
        "Рабочие задачи",
        ["user"],
        ["Исполнитель, группа, содержание, срок и статус задачи"],
        ["DIRECTOR", "ADMIN", "TEACHER"],
    ),
    (
        "notifications",
        "Уведомления",
        ["user"],
        ["Получатель, тип события, ссылка на объект и состояние прочтения"],
        ["DIRECTOR", "ADMIN", "TEACHER"],
    ),
    (
        "security_audit",
        "Сеансы и журнал действий",
        ["user"],
        [
            "Хеш секрета сеанса, сроки, отзыв, автор и тип действия, идентификатор объекта"
        ],
        ["DIRECTOR", "ADMIN", "TEACHER", "PARENT"],
    ),
    (
        "rights_requests",
        "Обращения и юридические свидетельства",
        ["user", "child"],
        [
            "Заявитель, цель, версия документа, дата оригинала, тип обращения и история статусов"
        ],
        ["DIRECTOR", "ADMIN", "TEACHER", "PARENT"],
    ),
]


def draft_inventory() -> list[dict]:
    return [
        {
            "id": f"draft:{code}",
            "code": code,
            "version": "draft-inventory-v1",
            "title": title,
            "document_id": None,
            "consent_document_id": None,
            "subject_categories": subjects,
            "data_categories": categories,
            "operations": [
                "Технический учёт; разрешённый юридический перечень не утверждён"
            ],
            "access_roles": roles,
            "legal_basis": None,
            "retention": None,
            "processors": None,
            "locations": None,
            "consent_required": None,
            "ready": False,
        }
        for code, title, subjects, categories, roles in _INVENTORY
    ]


class OperatorInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    address: str | None = Field(default=None, max_length=500)
    contact: str | None = Field(default=None, max_length=200)
    registration_details: str | None = Field(default=None, max_length=500)
    role: str | None = Field(default=None, max_length=500)


class DocumentInput(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    id: UUID
    organization_id: UUID | None = None
    document_type: Literal["policy", "notice", "paper_consent"]
    version: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=200)
    operator: OperatorInput
    content: str = Field(min_length=1, max_length=100_000)
    content_hash: str = Field(pattern="^[a-f0-9]{64}$")
    status: Literal["draft", "published", "retired"] = "draft"
    approved_at: datetime | None = None
    approval_reference: str | None = Field(default=None, max_length=200)
    effective_at: datetime | None = None

    @model_validator(mode="after")
    def publication(self):
        if fingerprint(self.content) != self.content_hash:
            raise ValueError("Document fingerprint mismatch")
        for value in (self.approved_at, self.effective_at):
            if value is not None and value.tzinfo is None:
                raise ValueError("Legal timestamps require timezone")
        if self.status != "draft":
            values = [
                self.operator.name,
                self.operator.address,
                self.operator.contact,
                self.operator.role,
                self.approval_reference,
                self.content,
                self.version,
                self.title,
            ]
            if (
                not self.approved_at
                or not self.effective_at
                or any(not v or not v.strip() or UNRESOLVED.search(v) for v in values)
            ):
                raise ValueError(
                    "Publication requires approved complete operator-specific content"
                )
            if self.approved_at > datetime.now(UTC):
                raise ValueError("Approval cannot be in the future")
        return self


class PurposeInput(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    id: UUID
    organization_id: UUID
    code: str
    version: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=200)
    document_id: UUID
    consent_document_id: UUID | None = None
    subject_categories: list[Literal["user", "child"]] = Field(min_length=1)
    data_categories: list[str] = Field(min_length=1, max_length=30)
    operations: list[str] = Field(min_length=1, max_length=30)
    access_roles: list[Literal["DIRECTOR", "ADMIN", "TEACHER", "PARENT"]] = Field(
        min_length=1
    )
    legal_basis: str | None = None
    retention: str | None = None
    processors: list[str] | None = None
    locations: list[str] | None = None
    consent_required: bool | None = None
    enabled: bool = False

    @model_validator(mode="after")
    def approved_basis(self):
        if self.code not in PURPOSE_CODES:
            raise ValueError("Deferred or unknown purpose")
        if self.enabled:
            values = [
                self.legal_basis,
                self.retention,
                self.title,
                *self.data_categories,
                *self.operations,
                *(self.processors or []),
                *(self.locations or []),
            ]
            if self.consent_required is None or any(
                not v or not v.strip() or UNRESOLVED.search(v) for v in values
            ):
                raise ValueError(
                    "Enabled purpose requires reviewed basis and retention"
                )
            if self.consent_required and not self.consent_document_id:
                raise ValueError("Separate paper document required")
        return self


class CatalogInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    synthetic: bool = False
    documents: list[DocumentInput] = Field(max_length=100)
    purposes: list[PurposeInput] = Field(max_length=100)


def document_is_effective(document) -> bool:
    try:
        value = DocumentInput.model_validate(document)
    except ValueError:
        return False
    return value.status == "published" and value.effective_at <= datetime.now(UTC)


def install_catalog(db, catalog: CatalogInput, *, reviewed: bool, app_env: str) -> None:
    """Explicit operator command; one transaction, immutable versions, no auto-approval."""
    from app.models.privacy import LegalDocument, ProcessingPurpose
    from app.services.tenant_locks import lock_tenant

    organizations = {
        d.organization_id for d in catalog.documents if d.organization_id
    } | {p.organization_id for p in catalog.purposes}
    for organization_id in sorted(organizations, key=str):
        lock_tenant(db, organization_id)

    if catalog.synthetic and app_env not in {"test", "development"}:
        raise ValueError(
            "Synthetic catalogs cannot be installed in shared environments"
        )
    if not reviewed and (
        any(d.status != "draft" for d in catalog.documents)
        or any(p.enabled for p in catalog.purposes)
    ):
        raise ValueError("Explicit reviewed publication required")
    for value in catalog.documents:
        if catalog.synthetic and not value.operator.name.startswith("СИНТЕТИЧЕСКИЙ"):
            raise ValueError("Synthetic operator must be visibly labeled")
        existing = db.get(LegalDocument, value.id)
        data = value.model_dump(mode="python")
        data["operator"] = value.operator.model_dump()
        if existing:
            previous = DocumentInput.model_validate(existing).model_dump()
            if previous == value.model_dump():
                continue
            if (
                value.status == "retired"
                and {**previous, "status": "retired"} == value.model_dump()
            ):
                existing.status = "retired"
                continue
            raise ValueError(
                "Document versions are immutable; use a new UUID and version"
            )
        db.add(LegalDocument(**data))
    db.flush()
    for value in catalog.purposes:
        document = db.get(LegalDocument, value.document_id)
        if (
            not document
            or document.organization_id != value.organization_id
            or document.document_type not in {"policy", "notice"}
        ):
            raise ValueError("Purpose document scope mismatch")
        if value.enabled and not document_is_effective(document):
            raise ValueError("Enabled purpose requires an effective published document")
        if value.consent_document_id:
            consent = db.get(LegalDocument, value.consent_document_id)
            if (
                not consent
                or consent.organization_id != value.organization_id
                or consent.document_type != "paper_consent"
            ):
                raise ValueError("Consent document scope mismatch")
            if value.enabled and not document_is_effective(consent):
                raise ValueError("Consent document must be published")
        existing = db.get(ProcessingPurpose, value.id)
        if existing:
            if PurposeInput.model_validate(existing) != value:
                raise ValueError(
                    "Purpose versions are immutable; retire their document and create a new version"
                )
        else:
            db.add(ProcessingPurpose(**value.model_dump()))
    db.flush()
