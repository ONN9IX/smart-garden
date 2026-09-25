"""Parent account responses; plaintext exists only in create/reset responses."""

from pydantic import BaseModel

from app.schemas.guardian import ParentAccountSummary


class TemporaryCredentials(BaseModel):
    account: ParentAccountSummary
    temporary_password: str
