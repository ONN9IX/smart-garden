# Stage 4 — Data model and decisions

Status: DESIGN FROZEN after merge of this design PR.
Baseline: Stage 1–3 FROZEN, latest migration 0009, current architecture from AGENTS.md and docs/CURRENT_STATE.md.

## 1. Scope

Stage 4 adds:
1. Audit Log — immutable tenant-scoped business audit for critical mutations.
2. Announcements — management announcements targeted to the whole kindergarten or one group.
3. Dashboard — operational snapshot for DIRECTOR/ADMIN using current garden-local date.

Out of scope: TEACHER, full PARENT UI, push/email/SMS, files/attachments, payments, medical data, SCUD/tablets, biometrics, chat, external analytics/integrations.

## 2. Architecture baseline

Unchanged: Next.js/React/TypeScript; FastAPI/Python; PostgreSQL; SQLAlchemy/Alembic; /api/v1; snake_case; UUID; server-side session + HttpOnly cookie; Argon2id; tenant from authenticated User; current RBAC; Organization.timezone IANA.

## 3. AuditEvent

Migration 0010 creates audit_events.

Fields:
- id UUID PK
- organization_id UUID NOT NULL FK organizations.id
- actor_user_id UUID NOT NULL FK users.id
- action VARCHAR(64) NOT NULL
- entity_type VARCHAR(32) NOT NULL
- entity_id UUID NULL
- details JSONB NOT NULL DEFAULT {}
- created_at TIMESTAMPTZ NOT NULL server default now()

Indexes:
- organization_id + created_at
- organization_id + entity_type + entity_id
- organization_id + actor_user_id + created_at

Audit rows are append-only. No public PATCH/DELETE.

### Audit content policy

details is never a copy of request/response bodies.

Allowed only:
- changed field names
- status/role/relation enums
- technical UUIDs where necessary
- before/after Attendance status/time values when needed to understand a correction

Forbidden:
- passwords, hashes, temporary passwords, tokens
- request bodies
- child/guardian/employee names
- phone/email/address/birth_date
- medical data
- announcement title/body
- arbitrary notes

Audit and business mutation commit in the same DB transaction.

### Audit scope

Log:
- Group create/update/archive/restore
- Child create/update/archive/restore
- Guardian create/update/archive/restore
- ChildGuardian create/update/archive/restore as supported
- Employee create/update/archive/restore
- PARENT/ADMIN account create/reset/block/unblock
- Attendance create/update
- Announcement create/update/archive

Role-change operations are not added in Stage 4. Reads are not audit-logged.

## 4. Announcement

Migration 0011 creates announcements.

Fields:
- id UUID PK
- organization_id UUID NOT NULL FK organizations.id
- target_type VARCHAR(16): all|group
- group_id UUID NULL FK groups.id
- title VARCHAR(120) NOT NULL
- body VARCHAR(2000) NOT NULL
- status VARCHAR(16): active|archived
- created_by UUID NOT NULL FK users.id
- updated_by UUID NOT NULL FK users.id
- archived_at TIMESTAMPTZ NULL
- created_at / updated_at TIMESTAMPTZ

Rules:
- all => group_id NULL
- group => group_id NOT NULL
- title/body non-empty after trim
- DIRECTOR/ADMIN manage own-tenant announcements
- create publishes immediately as active
- no hard delete, no restore, no draft
- active group required for new/update group target
- later group archive does not delete existing announcement
- no attachments/push/email/SMS
- PARENT has no Stage 4 Announcement UI/API
- audit announcement mutations without storing title/body in Audit details

## 5. Dashboard

No new table.

Dashboard is computed for garden-local today from Organization.timezone.

Response:
- date
- active_children
- present
- absent
- unknown
- active_groups
- active_employees
- groups[]: id, name, active_children, present, absent, unknown

Count only active children in active groups.
Missing Attendance row = unknown; explicit unknown = unknown.
Dashboard group aggregation uses the child's current active group because Dashboard is a current operational view. Attendance history keeps its saved group snapshot.

No trends/history charts/revenue/predictive analytics.

## 6. RBAC

- DIRECTOR: Dashboard, Announcement manage, Audit read
- ADMIN: Dashboard, Announcement manage, no Audit read
- PARENT: no Stage 4 management access

Audit events are written for approved mutations regardless of DIRECTOR/ADMIN actor.

## 7. Tenant isolation

All Stage 4 queries use authenticated User organization.
No organization_id from client.
Foreign Announcement/Audit UUID => 404.
Foreign Group target => 404.
Dashboard accepts no tenant id.
Audit filters never bypass tenant scope.

## 8. Personal data / 152-FZ

Dashboard adds no new PII fields.

Announcement title/body are necessary free text and may accidentally contain PII. Purpose is limited to operational kindergarten announcements. UI must warn not to enter passwords, medical information or unnecessary/sensitive personal data. No attachments.

AuditEvent is personal data processing because actor_user_id records identifiable user activity. Audit read access is DIRECTOR-only. Audit details are minimized and do not duplicate business PII/secrets.

Retention/deletion policy for real production Audit/Announcements is deferred to the separate pilot/production legal/infrastructure review. Dev/test/preview remain synthetic only.

## 9. Migration order

- 0010_audit_events
- 0011_announcements

Both require PostgreSQL upgrade/downgrade coverage and must preserve Stage 1–3 data.

## 10. Delivery split

1. STAGE4-AUDIT — migration 0010, audit service/instrumentation, Audit API/UI/tests.
2. STAGE4-OPS — migration 0011, Announcements + Dashboard backend/frontend, announcement audit integration/tests.
3. Stage 4 acceptance.

This split is frozen unless implementation uncovers an architecture/API/auth/RBAC/tenant/privacy blocker requiring Chat decision.
