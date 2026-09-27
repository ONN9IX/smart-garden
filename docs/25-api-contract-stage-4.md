# API Contract Stage 4 — Dashboard / Announcements / Audit

Base: /api/v1. Existing Stage 1–3 contracts remain frozen.

Common:
- JSON snake_case
- UUID strings
- timestamps RFC3339 UTC
- dates YYYY-MM-DD
- HttpOnly server-side session
- tenant only from authenticated User
- existing error envelope

## 1. Dashboard

GET /dashboard/summary
Roles: DIRECTOR, ADMIN.

200 response fields:
- date
- active_children
- present
- absent
- unknown
- active_groups
- active_employees
- groups[] with id, name, active_children, present, absent, unknown

date = garden-local today from Organization.timezone.
PARENT => 403.

## 2. Announcement transport

Fields:
- id
- target_type all|group
- group {id,name} or null
- title
- body
- status active|archived
- created_by UUID
- updated_by UUID
- archived_at
- created_at
- updated_at

No organization_id.

GET /announcements
Roles DIRECTOR, ADMIN.
Query: status active|archived|all (default active), target_type optional, group_id optional.
Foreign group_id => 404.
Response: {items:[...]}.

POST /announcements
Roles DIRECTOR, ADMIN.
Body: target_type, group_id, title, body.
201 detail.
Extra fields including organization_id/created_by/updated_by/status => 400.

GET /announcements/{id}
Roles DIRECTOR, ADMIN.
Own tenant 200; foreign/missing 404.

PATCH /announcements/{id}
Roles DIRECTOR, ADMIN.
Non-empty subset of target_type/group_id/title/body.
Archived => 409 ANNOUNCEMENT_ARCHIVED.
200 detail.

POST /announcements/{id}/archive
Roles DIRECTOR, ADMIN.
No body, idempotent, 200 detail.

PARENT => 403 on all Announcement endpoints.

## 3. Audit transport

Fields:
- id
- action
- entity_type
- entity_id nullable
- actor {id,username,role}
- details
- created_at

No organization_id and no business-person names.

GET /audit
DIRECTOR only.
Query:
- entity_type optional
- action optional
- actor_user_id optional
- date_from/date_to optional YYYY-MM-DD
- limit default 50, max 100
- offset default 0

Response: items + limit + offset.
Sort created_at DESC, id DESC.
ADMIN/PARENT => 403.

GET /audit/{id}
DIRECTOR only.
Own tenant 200; foreign/missing 404.

No public Audit POST/PATCH/DELETE.

## 4. Audit details privacy contract

May contain only:
- changed field names
- status/role/relation enums
- technical UUIDs
- Attendance before/after status/time when needed

Never contain:
- passwords/hashes/temp passwords/tokens
- request bodies
- announcement title/body
- names/phone/email/birth_date/address
- medical/sensitive free text

## 5. Errors

Existing errors remain.
Add:
- 409 ANNOUNCEMENT_ARCHIVED

Validation 400, unauthenticated 401, role denial 403, foreign/missing object 404.

## 6. Compatibility

No Stage 1–3 request/response changes.

Stage 4 adds:
- Dashboard summary endpoint
- Announcement endpoints
- Audit read endpoints

Existing mutation endpoints gain internal audit side effects only; their public responses remain unchanged.
