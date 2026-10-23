"""Synthetic-only catalog factories. Never used by runtime seed or production."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.services.privacy_catalog import CatalogInput, fingerprint, install_catalog


def synthetic_catalog(organization_id):
    now = datetime.now(UTC) - timedelta(days=2)
    operator = {
        "name": "СИНТЕТИЧЕСКИЙ тестовый оператор",
        "address": "Вымышленный адрес для теста",
        "contact": "privacy@example.test",
        "role": "Синтетическая роль для теста",
    }
    documents = []
    for kind in ("policy", "paper_consent"):
        text = f"СИНТЕТИЧЕСКИЙ документ {kind}. Не юридический документ и не основание для реального пилота."
        documents.append(
            {
                "id": uuid4(),
                "organization_id": organization_id,
                "document_type": kind,
                "version": "synthetic-v1",
                "title": f"СИНТЕТИЧЕСКИЙ {kind}",
                "operator": operator,
                "content": text,
                "content_hash": fingerprint(text),
                "status": "published",
                "approved_at": now,
                "effective_at": now,
                "approval_reference": "СИНТЕТИЧЕСКАЯ проверка теста",
            }
        )
    base = {
        "organization_id": organization_id,
        "version": "synthetic-v1",
        "document_id": documents[0]["id"],
        "subject_categories": ["user", "child"],
        "data_categories": ["Синтетические данные"],
        "operations": ["Синтетический учёт"],
        "access_roles": ["DIRECTOR", "ADMIN", "TEACHER", "PARENT"],
        "legal_basis": "СИНТЕТИЧЕСКОЕ основание, не применимо к реальным данным",
        "retention": "СИНТЕТИЧЕСКОЕ условие до завершения теста",
        "processors": None,
        "locations": None,
        "enabled": True,
    }
    purposes = [
        {
            **base,
            "id": uuid4(),
            "code": "account_access",
            "title": "СИНТЕТИЧЕСКИЙ доступ",
            "consent_required": False,
        },
        {
            **base,
            "id": uuid4(),
            "code": "family_contacts",
            "title": "СИНТЕТИЧЕСКАЯ отдельная цель",
            "consent_required": True,
            "consent_document_id": documents[1]["id"],
        },
    ]
    return CatalogInput(synthetic=True, documents=documents, purposes=purposes)


def install_synthetic_catalog(db, organization_id):
    catalog = synthetic_catalog(organization_id)
    install_catalog(db, catalog, reviewed=True, app_env="test")
    return catalog
