# Stage 4 — Backend specification

Design source: docs/22-stage-4-data-model-and-decisions.md

## 1. Audit backend

Create AuditEvent migration/model/service.
Use one internal audit writer with explicit whitelisted structured details.
Audit writes occur in the same SQLAlchemy transaction as the audited mutation.
Do not change frozen Stage 1–3 public API responses solely to support audit.

### Audit API

DIRECTOR only:
- GET /api/v1/audit
- GET /api/v1/audit/{id}

List filters:
- entity_type optional
- action optional
- actor_user_id optional UUID
- date_from/date_to optional YYYY-MM-DD
- limit default 50, max 100
- offset default 0

Sort newest first by created_at DESC, id DESC.
Response: items + limit + offset.

Audit transport:
- id
- action
- entity_type
- entity_id nullable
- actor {id, username, role}
- details
- created_at

No organization_id.
ADMIN/PARENT => 403.
Foreign audit id => 404.

## 2. Announcement backend

Routes for DIRECTOR/ADMIN:
- GET /api/v1/announcements
- POST /api/v1/announcements
- GET /api/v1/announcements/{id}
- PATCH /api/v1/announcements/{id}
- POST /api/v1/announcements/{id}/archive

List filters:
- status active|archived|all, default active
- target_type all|group optional
- group_id UUID optional

Create/PATCH fields:
- target_type
- group_id nullable
- title
- body

Validation:
- title 1–120 after trim
- body 1–2000 after trim
- all requires group_id null
- group requires active same-tenant group
- client cannot set organization_id/created_by/updated_by/status
- archived announcement cannot be edited
- archive idempotent

Add ANNOUNCEMENT_ARCHIVED 409. Existing GROUP_ARCHIVED applies when target group is archived.
PARENT => 403.

Announcement create/update/archive writes Audit events without title/body in details.

## 3. Dashboard backend

DIRECTOR/ADMIN:
- GET /api/v1/dashboard/summary

No tenant/date input. Date = authenticated Organization garden-local today.

Return:
- date
- active_children
- present
- absent
- unknown
- active_groups
- active_employees
- group rows with id/name/active_children/present/absent/unknown

Requirements:
- active children/groups only
- missing row = unknown
- explicit unknown = unknown
- current active child group for Dashboard grouping
- totals equal sum of group rows
- avoid N+1
- no persistence/audit for read
- PARENT => 403

## 4. Audit instrumentation

Instrument service/business layer, not router middleware.

For update events details may contain changed_fields and approved enum/time before/after values.

Account events never store password material.
Attendance may store old/new status/arrival/departure but never child name.
Announcement audit may store target_type/group_id/changed_fields but never title/body.

## 5. Transactions

Audit + mutation succeed/fail together.
Representative rollback tests must prove no partial business change and no orphan audit row.

## 6. Security/errors

Keep existing 400/401/403/404/409 semantics.
Never leak raw exceptions, tenant existence, PII or secrets.
No secrets in logs.

## 7. Required tests

Audit:
- migration round-trip
- DIRECTOR read
- ADMIN/PARENT denied
- tenant isolation
- filters/pagination
- append-only API
- representative events across Group/Child/Guardian/relation/Employee/account/Attendance
- no password/title/body/PII leakage
- transaction rollback

Announcement:
- constraints
- tenant/group validation
- create/read/update/archive
- archived edit denied
- PARENT denied
- audit generated
- cross-tenant denied

Dashboard:
- counters
- explicit/missing unknown
- garden-local date
- current-group aggregation after transfer
- archived child/group exclusion
- tenant isolation
- PARENT denied

Full regression remains CI responsibility.
