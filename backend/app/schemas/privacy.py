"""Closed request contracts: no tenant selector, uploads or free-form personal text."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AttestationInput(StrictInput):
    profile_type: Literal["guardian", "employee"]
    profile_ids: list[UUID] = Field(min_length=1, max_length=100)
    purpose_id: UUID
    documents_confirmed: Literal[True]


class PaperConsentInput(StrictInput):
    purpose_id: UUID
    document_id: UUID
    subject_user_id: UUID | None = None
    child_id: UUID | None = None
    guardian_id: UUID | None = None
    received_on: date
    original_held_confirmed: Literal[True]
    authority_confirmed: Literal[True]
    idempotency_key: UUID

    @model_validator(mode="after")
    def subject(self):
        own = (
            self.subject_user_id is not None
            and self.child_id is None
            and self.guardian_id is None
        )
        child = (
            self.subject_user_id is None
            and self.child_id is not None
            and self.guardian_id is not None
        )
        if not (own or child):
            raise ValueError("Choose one subject")
        return self


class RequestInput(StrictInput):
    kind: Literal["access", "correction", "withdrawal", "stop_processing", "erasure"]
    child_id: UUID | None = None
    idempotency_key: UUID


class RequestTransition(StrictInput):
    status: Literal["verifying", "in_review", "completed", "declined"]
    expected_status: Literal["submitted", "verifying", "in_review"]
    due_at: datetime | None = None
    decision_code: (
        Literal[
            "fulfilled_offline",
            "independent_legal_basis",
            "authority_not_verified",
            "not_applicable",
        ]
        | None
    ) = None
    # Closing a ticket only records a reviewed off-system outcome.
    outcome_confirmed: bool = False
