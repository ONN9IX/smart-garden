"""Public management error shapes for OpenAPI; no raw exception detail is exposed."""

from app.schemas.auth import ErrorResponse

MANAGEMENT_ERRORS = {
    status: {"model": ErrorResponse}
    for status in (400, 401, 403, 404, 409, 500)
}
