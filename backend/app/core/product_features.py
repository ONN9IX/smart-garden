"""Static product module gates for the current Smart Garden product baseline.

OFF modules are preserved in code/data but hidden from product surfaces and blocked at API entry.
This is intentionally not tenant-configurable yet.
"""

PRODUCT_FEATURES: dict[str, bool] = {
    "polls": False,
    "incidents": False,
    "diary": False,
    "photos": False,
    "document_notices": False,
    "contracts_billing": False,
    "entry_kiosk": False,
    "development_support": False,
    "tenant_subscription": False,
}

_DISABLED_PREFIXES: tuple[tuple[str, str], ...] = (
    ("polls", "/api/v1/teacher/polls"),
    ("polls", "/api/v1/parent/polls"),
    ("polls", "/api/v1/teacher-management/polls"),
    ("incidents", "/api/v1/teacher/incidents"),
    ("incidents", "/api/v1/teacher-management/incidents"),
    ("diary", "/api/v1/teacher/diary"),
    ("diary", "/api/v1/teacher-management/diary"),
    ("photos", "/api/v1/teacher/photos"),
    ("photos", "/api/v1/teacher/photo-consents"),
    ("photos", "/api/v1/parent/photos"),
    ("photos", "/api/v1/teacher-management/photo-consents"),
    ("document_notices", "/api/v1/teacher/document-notices"),
    ("document_notices", "/api/v1/teacher-management/document-notices"),
)


def feature_enabled(feature: str) -> bool:
    return PRODUCT_FEATURES.get(feature, True)


def is_api_feature_disabled(path: str) -> bool:
    for feature, prefix in _DISABLED_PREFIXES:
        if path.startswith(prefix) and not feature_enabled(feature):
            return True

    # PARENT diary path contains the child UUID before /diary.
    return (
        path.startswith("/api/v1/parent/children/")
        and path.endswith("/diary")
        and not feature_enabled("diary")
    )
