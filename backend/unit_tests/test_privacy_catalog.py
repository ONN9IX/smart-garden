"""Approval, purpose and version validation without a database."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.services.privacy_catalog import (
    CatalogInput,
    DocumentInput,
    PurposeInput,
    fingerprint,
)
from tests.privacy_helpers import synthetic_catalog


@pytest.mark.parametrize(
    "change",
    [
        {"approved_at": None},
        {"approval_reference": None},
        {"effective_at": None},
        {"content_hash": "0" * 64},
        {"version": "[ДАТА УТВЕРЖДЕНИЯ]"},
        {"approved_at": datetime.now(UTC) + timedelta(days=2)},
        {"operator": {"name": "[ОПЕРАТОР]", "address": "[РЕКВИЗИТЫ]", "contact": None}},
    ],
)
def test_cannot_publish_unapproved_or_incomplete_text(change):
    original = synthetic_catalog(uuid4()).documents[0].model_dump()
    with pytest.raises(ValidationError):
        DocumentInput.model_validate({**original, **change})


def test_drafts_and_future_effective_versions_remain_non_effective():
    from app.services.privacy_catalog import document_is_effective

    doc = synthetic_catalog(uuid4()).documents[0]
    assert document_is_effective(doc)
    assert not document_is_effective(
        doc.model_copy(update={"status": "draft", "approved_at": None})
    )
    assert not document_is_effective(
        doc.model_copy(update={"effective_at": datetime.now(UTC) + timedelta(days=2)})
    )


@pytest.mark.parametrize(
    "change",
    [
        {"code": "photos"},
        {"code": "marketing"},
        {"code": "medical"},
        {"legal_basis": None},
        {"retention": None},
        {"consent_required": None},
        {"consent_required": True, "consent_document_id": None},
    ],
)
def test_off_unknown_or_unapproved_purposes_cannot_be_enabled(change):
    original = synthetic_catalog(uuid4()).purposes[0].model_dump()
    with pytest.raises(ValidationError):
        PurposeInput.model_validate({**original, **change})


def test_content_hash_is_exact_and_catalog_does_not_accept_unrecognized_approval_fields():
    assert fingerprint("policy") != fingerprint("policy\n")
    with pytest.raises(ValidationError):
        CatalogInput(documents=[], purposes=[], legal_approved=True)
