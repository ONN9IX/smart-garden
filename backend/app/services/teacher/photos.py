"""Consent-gated authenticated synthetic photo storage for non-production environments."""

import struct
import tempfile
import uuid
from pathlib import Path
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.models.child import Child
from app.models.photo import PhotoAsset, PhotoAssetChild, PhotoConsent
from app.models.user import User
from app.schemas.teacher.contracts import PhotoConsentResponse, PhotoResponse
from app.services import audit
from app.services.auth import utc_now
from app.services.teacher import access

MAX_PHOTO_BYTES = 5 * 1024 * 1024
STORAGE_ROOT = Path(tempfile.gettempdir()) / "smart-garden-stage6-photos"


def _consent_response(item: PhotoConsent) -> PhotoConsentResponse:
    return PhotoConsentResponse(
        id=item.id, child_id=item.child_id, status=item.status, scope=item.scope,
        effective_from=item.effective_from, effective_to=item.effective_to,
    )


def teacher_consents(db: Session, actor: User, group_id: UUID) -> list[PhotoConsentResponse]:
    access.teacher_group(db, actor, group_id)
    items = db.scalars(
        select(PhotoConsent)
        .join(Child, Child.id == PhotoConsent.child_id)
        .where(
            PhotoConsent.organization_id == actor.organization_id,
            Child.organization_id == actor.organization_id,
            Child.group_id == group_id,
            Child.status == "active",
        ).order_by(Child.last_name, Child.first_name, PhotoConsent.child_id)
    )
    return [_consent_response(item) for item in items]


def _active_consent(db: Session, actor: User, child_id: UUID) -> bool:
    now = utc_now()
    return db.scalar(select(PhotoConsent.id).where(
        PhotoConsent.organization_id == actor.organization_id,
        PhotoConsent.child_id == child_id,
        PhotoConsent.scope == "group_photo_report",
        PhotoConsent.status == "granted",
        PhotoConsent.effective_from <= now,
        or_(PhotoConsent.effective_to.is_(None), PhotoConsent.effective_to > now),
    )) is not None


def _child_ids(db: Session, actor: User, photo_id: UUID) -> list[UUID]:
    return list(db.scalars(select(PhotoAssetChild.child_id).where(
        PhotoAssetChild.organization_id == actor.organization_id,
        PhotoAssetChild.photo_asset_id == photo_id,
    ).order_by(PhotoAssetChild.child_id)))


def _photo(db: Session, actor: User, item: PhotoAsset) -> PhotoResponse:
    return PhotoResponse(
        id=item.id, group_id=item.group_id, child_ids=_child_ids(db, actor, item.id),
        mime_type=item.mime_type, size_bytes=item.size_bytes, captured_at=item.captured_at,
        status=item.status, created_at=item.created_at,
    )


def _all_consented(db: Session, actor: User, child_ids: list[UUID]) -> bool:
    return bool(child_ids) and all(_active_consent(db, actor, child_id) for child_id in child_ids)


def upload(
    db: Session, actor: User, group_id: UUID, child_ids: list[UUID], mime_type: str, raw: bytes,
) -> PhotoResponse:
    if get_settings().app_env in {"staging", "production"}:
        raise AppError(403, "FORBIDDEN")
    access.teacher_group(db, actor, group_id)
    unique_child_ids = list(dict.fromkeys(child_ids))
    if not unique_child_ids:
        raise AppError(400, "VALIDATION_ERROR", "child_ids")
    for child_id in unique_child_ids:
        child = access.teacher_child(db, actor, child_id)
        if child.group_id != group_id or not _active_consent(db, actor, child.id):
            raise AppError(404, "NOT_FOUND")
    sanitized, normalized_type, suffix = _sanitize(raw, mime_type)
    storage_key = f"{uuid.uuid4().hex}{suffix}"
    STORAGE_ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = STORAGE_ROOT / storage_key
    path.write_bytes(sanitized)
    try:
        item = PhotoAsset(
            organization_id=actor.organization_id, group_id=group_id, storage_key=storage_key,
            mime_type=normalized_type, size_bytes=len(sanitized), uploaded_by=actor.id, status="active",
        )
        db.add(item)
        db.flush()
        db.add_all([PhotoAssetChild(
            organization_id=actor.organization_id, photo_asset_id=item.id, child_id=child_id,
        ) for child_id in unique_child_ids])
        audit.write(db, actor, "photo.create", "photo_asset", item.id, {"group_id": str(group_id)})
        db.commit()
        db.refresh(item)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return _photo(db, actor, item)


def teacher_photos(db: Session, actor: User, group_id: UUID) -> list[PhotoResponse]:
    access.teacher_group(db, actor, group_id)
    items = db.scalars(select(PhotoAsset).where(
        PhotoAsset.organization_id == actor.organization_id,
        PhotoAsset.group_id == group_id,
        PhotoAsset.status == "active",
    ).order_by(PhotoAsset.created_at.desc(), PhotoAsset.id.desc()))
    return [_photo(db, actor, item) for item in items if _all_consented(db, actor, _child_ids(db, actor, item.id))]


def parent_photos(db: Session, actor: User, child_id: UUID) -> list[PhotoResponse]:
    access.parent_child(db, actor, child_id)
    items = db.scalars(
        select(PhotoAsset)
        .join(PhotoAssetChild, PhotoAssetChild.photo_asset_id == PhotoAsset.id)
        .where(
            PhotoAsset.organization_id == actor.organization_id,
            PhotoAsset.status == "active",
            PhotoAssetChild.organization_id == actor.organization_id,
            PhotoAssetChild.child_id == child_id,
        ).order_by(PhotoAsset.created_at.desc(), PhotoAsset.id.desc())
    )
    return [_photo(db, actor, item) for item in items if _all_consented(db, actor, _child_ids(db, actor, item.id))]


def teacher_content(db: Session, actor: User, photo_id: UUID) -> tuple[bytes, str]:
    item = _asset(db, actor, photo_id)
    access.teacher_group(db, actor, item.group_id)
    child_ids = _child_ids(db, actor, item.id)
    if not _all_consented(db, actor, child_ids):
        raise AppError(404, "NOT_FOUND")
    return _read(item)


def parent_content(db: Session, actor: User, photo_id: UUID) -> tuple[bytes, str]:
    item = _asset(db, actor, photo_id)
    child_ids = _child_ids(db, actor, item.id)
    if not _all_consented(db, actor, child_ids):
        raise AppError(404, "NOT_FOUND")
    if not any(_parent_can_read(db, actor, child_id) for child_id in child_ids):
        raise AppError(404, "NOT_FOUND")
    return _read(item)


def _parent_can_read(db: Session, actor: User, child_id: UUID) -> bool:
    try:
        access.parent_child(db, actor, child_id)
    except AppError:
        return False
    return True


def _asset(db: Session, actor: User, photo_id: UUID) -> PhotoAsset:
    item = db.scalar(select(PhotoAsset).where(
        PhotoAsset.id == photo_id,
        PhotoAsset.organization_id == actor.organization_id,
        PhotoAsset.status == "active",
    ))
    if item is None:
        raise AppError(404, "NOT_FOUND")
    return item


def _read(item: PhotoAsset) -> tuple[bytes, str]:
    path = STORAGE_ROOT / item.storage_key
    if not path.is_file():
        raise AppError(404, "NOT_FOUND")
    return path.read_bytes(), item.mime_type


def _sanitize(raw: bytes, mime_type: str) -> tuple[bytes, str, str]:
    if not raw or len(raw) > MAX_PHOTO_BYTES:
        raise AppError(400, "VALIDATION_ERROR", "file")
    if mime_type == "image/jpeg" and raw.startswith(b"\xff\xd8"):
        cleaned = _strip_jpeg_metadata(raw)
        return cleaned, "image/jpeg", ".jpg"
    if mime_type == "image/png" and raw.startswith(b"\x89PNG\r\n\x1a\n"):
        cleaned = _strip_png_metadata(raw)
        return cleaned, "image/png", ".png"
    raise AppError(400, "VALIDATION_ERROR", "file")


def _strip_jpeg_metadata(raw: bytes) -> bytes:
    output = bytearray(raw[:2])
    cursor = 2
    while cursor < len(raw):
        marker_start = cursor
        if raw[cursor] != 0xFF:
            raise AppError(400, "VALIDATION_ERROR", "file")
        while cursor < len(raw) and raw[cursor] == 0xFF:
            cursor += 1
        if cursor >= len(raw):
            raise AppError(400, "VALIDATION_ERROR", "file")
        marker = raw[cursor]
        cursor += 1
        if marker == 0xDA:
            output.extend(raw[marker_start:])
            return bytes(output)
        if marker == 0xD9:
            output.extend(b"\xff\xd9")
            return bytes(output)
        if marker in {0x01, *range(0xD0, 0xD9)}:
            output.extend(raw[marker_start:cursor])
            continue
        if cursor + 2 > len(raw):
            raise AppError(400, "VALIDATION_ERROR", "file")
        length = int.from_bytes(raw[cursor:cursor + 2], "big")
        end = cursor + length
        if length < 2 or end > len(raw):
            raise AppError(400, "VALIDATION_ERROR", "file")
        if marker == 0xE0 or not (0xE1 <= marker <= 0xEF or marker == 0xFE):
            output.extend(raw[marker_start:end])
        cursor = end
    raise AppError(400, "VALIDATION_ERROR", "file")


def _strip_png_metadata(raw: bytes) -> bytes:
    output = bytearray(raw[:8])
    cursor = 8
    saw_header = saw_data = saw_end = False
    retained = {b"IHDR", b"PLTE", b"IDAT", b"IEND", b"tRNS"}
    while cursor + 12 <= len(raw):
        length = struct.unpack(">I", raw[cursor:cursor + 4])[0]
        end = cursor + 12 + length
        if end > len(raw):
            raise AppError(400, "VALIDATION_ERROR", "file")
        chunk_type = raw[cursor + 4:cursor + 8]
        if chunk_type in retained:
            output.extend(raw[cursor:end])
        saw_header = saw_header or chunk_type == b"IHDR"
        saw_data = saw_data or chunk_type == b"IDAT"
        saw_end = saw_end or chunk_type == b"IEND"
        cursor = end
        if chunk_type == b"IEND":
            break
    if not (saw_header and saw_data and saw_end) or cursor != len(raw):
        raise AppError(400, "VALIDATION_ERROR", "file")
    return bytes(output)
