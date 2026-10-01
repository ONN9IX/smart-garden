import pytest
from fastapi.testclient import TestClient

from app.core.product_features import PRODUCT_FEATURES, is_api_feature_disabled
from app.main import app


@pytest.mark.parametrize(
    ("feature", "path"),
    [
        ("polls", "/api/v1/teacher/polls"),
        ("polls", "/api/v1/parent/polls"),
        ("incidents", "/api/v1/teacher/incidents"),
        ("diary", "/api/v1/teacher/diary"),
        ("diary", "/api/v1/parent/children/00000000-0000-4000-8000-000000000001/diary"),
        ("photos", "/api/v1/teacher/photos"),
        ("photos", "/api/v1/teacher/photo-consents"),
        ("photos", "/api/v1/parent/photos"),
        ("document_notices", "/api/v1/teacher/document-notices"),
        ("document_notices", "/api/v1/teacher-management/document-notices"),
    ],
)
def test_deferred_module_paths_are_disabled_by_default(feature, path):
    assert PRODUCT_FEATURES[feature] is False
    assert is_api_feature_disabled(path) is True


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/teacher/attendance",
        "/api/v1/teacher/schedule",
        "/api/v1/teacher/announcements",
        "/api/v1/teacher/tasks",
        "/api/v1/teacher/notifications",
        "/api/v1/teacher/communications/threads",
        "/api/v1/parent/announcements",
        "/api/v1/parent/communications/threads",
        "/api/v1/attendance",
        "/api/v1/groups",
    ],
)
def test_core_paths_stay_enabled(path):
    assert is_api_feature_disabled(path) is False


def test_disabled_api_is_hidden_before_auth():
    with TestClient(app) as client:
        response = client.get("/api/v1/teacher/polls")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
