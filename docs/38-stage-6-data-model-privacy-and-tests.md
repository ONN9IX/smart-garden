# Stage 6 — data model, privacy and mandatory tests

**Status:** design-frozen by Issue #121; no table or migration is created by this design Issue.

Foundation must create the complete teacher-domain schema in one serialized migration from the then-current migration head. The current design baseline has migration head `0011`; the implementation Issue chooses the exact next filename.

Identifiers and entity references follow the project's PostgreSQL/UUID architecture. Where Issue #121 specifies bounded text but not a numeric bound, Foundation must choose and test a finite bound without expanding the field set or semantics.

## 1. Existing models reused

- Reuse `Attendance`; do not create a second attendance model or table.
- Reuse `Announcement`; do not create a second announcement model or table.
- Preserve the existing `Employee.user_id -> User.id` relationship.
- Preserve the existing `Child.group_id`, `ChildGuardian`, Group lifecycle, tenant and non-disclosure semantics.

## 2. New tables

### 2.1 `teacher_group_assignments`

Model: `TeacherGroupAssignment`.

| Field | Frozen definition |
|---|---|
| `id` | UUID primary key |
| `organization_id` | UUID, not null, FK to existing Organization |
| `employee_id` | UUID, not null, FK to existing Employee |
| `group_id` | UUID, not null, FK to existing Group |
| `status` | `active | archived` |
| `assigned_by` | UUID, not null, FK to existing User |
| `created_at` | timestamp |
| `archived_at` | nullable timestamp |

Constraints/indexes:

- all references use existing entities;
- unique `(employee_id, group_id)`; an archived assignment is restored, not duplicated;
- tenant/status indexes support `(organization_id, employee_id, status)` and `(organization_id, group_id, status)` access;
- assignment write validates same-tenant active Employee, active linked TEACHER User and same-tenant Group;
- teacher access additionally requires an active Group.

### 2.2 `group_schedule_items`

| Field | Frozen definition |
|---|---|
| `id` | UUID identifier |
| `organization_id` | tenant identifier |
| `group_id` | Group identifier |
| `weekday` | integer `0..6` |
| `start_time` | local time |
| `end_time` | local time |
| `title` | bounded text |
| `status` | `active | archived` |
| `created_by` | User identifier |
| `updated_by` | User identifier |
| `created_at` | timestamp |
| `updated_at` | timestamp |

Constraints/rules:

- `end_time > start_time`;
- recurring weekly schedule only in Stage 6;
- no attendance inference from schedule;
- Group, creator and updater are tenant-validated server-side.

### 2.3 `communication_threads`

| Field | Frozen definition |
|---|---|
| `id` | UUID identifier |
| `organization_id` | tenant identifier |
| `thread_type` | `group | direct` |
| `group_id` | Group identifier |
| `child_id` | nullable Child identifier |
| `guardian_id` | nullable Guardian identifier |
| `created_at` | timestamp |

Constraints/rules:

- group thread: `group_id` required; `child_id` and `guardian_id` null;
- direct thread: `group_id`, `child_id` and `guardian_id` required;
- direct context represents an active same-tenant `ChildGuardian` relation;
- one canonical group thread per Group;
- duplicate canonical direct thread for the same Child + Guardian + Group context is prevented;
- participant eligibility is derived server-side and is not stored as a client-defined list.

### 2.4 `communication_messages`

| Field | Frozen definition |
|---|---|
| `id` | UUID identifier |
| `organization_id` | tenant identifier |
| `thread_id` | CommunicationThread identifier |
| `sender_user_id` | User identifier, server-owned |
| `body` | bounded text |
| `created_at` | timestamp |

Constraints/rules:

- messages are immutable: no user edit and no user delete;
- sender and organization are always derived server-side;
- body is excluded from technical logs and `AuditEvent.details`.

### 2.5 `child_diary_entries`

| Field | Frozen definition |
|---|---|
| `id` | UUID identifier |
| `organization_id` | tenant identifier |
| `child_id` | Child identifier |
| `group_id` | historical/current-at-write Group snapshot |
| `date` | calendar date |
| `author_user_id` | User identifier, server-owned |
| `note` | bounded text |
| `created_at` | timestamp |
| `updated_at` | timestamp |

Constraints/rules:

- TEACHER creates/updates only for a currently assigned active Group and eligible active Child;
- PARENT reads only an actively linked Child;
- note text is excluded from technical logs and `AuditEvent.details`.

### 2.6 `polls`

| Field | Frozen definition |
|---|---|
| `id` | UUID identifier |
| `organization_id` | tenant identifier |
| `group_id` | Group identifier |
| `question` | bounded text |
| `status` | `active | closed | archived` |
| `closes_at` | nullable timestamp |
| `created_by` | User identifier, server-owned |
| `created_at` | timestamp |
| `updated_at` | timestamp |

### 2.7 `poll_options`

| Field | Frozen definition |
|---|---|
| `id` | UUID identifier |
| `poll_id` | Poll identifier |
| `label` | bounded text |
| `sort_order` | ordering value |

### 2.8 `poll_votes`

| Field | Frozen definition |
|---|---|
| `id` | UUID identifier |
| `organization_id` | tenant identifier |
| `poll_id` | Poll identifier |
| `option_id` | PollOption identifier |
| `voter_user_id` | PARENT User identifier, server-owned |
| `created_at` | timestamp |

Constraints/rules for polls/options/votes:

- one vote per PARENT User per Poll in Stage 6;
- voting is not anonymous;
- no multi-select;
- Option must belong to the selected Poll;
- PARENT eligibility is derived from the active child/group relation;
- no cross-group vote.

### 2.9 `incidents`

| Field | Frozen definition |
|---|---|
| `id` | UUID identifier |
| `organization_id` | tenant identifier |
| `group_id` | Group identifier |
| `child_id` | nullable Child identifier |
| `occurred_at` | timestamp |
| `category` | `safety | behavior | operational | other` |
| `description` | bounded text |
| `status` | `open | resolved` |
| `reported_by` | User identifier, server-owned |
| `resolved_by` | nullable User identifier, server-owned |
| `created_at` | timestamp |
| `updated_at` | timestamp |

No diagnosis, medication, medical document or medical-treatment field is allowed. Description is excluded from technical logs and `AuditEvent.details`. PARENT does not receive the raw Incident record in Stage 6.

### 2.10 `teacher_tasks`

| Field | Frozen definition |
|---|---|
| `id` | UUID identifier |
| `organization_id` | tenant identifier |
| `assignee_employee_id` | Employee identifier |
| `group_id` | nullable Group identifier |
| `title` | bounded text |
| `description` | nullable bounded text |
| `due_at` | nullable timestamp |
| `status` | `open | in_progress | done | cancelled` |
| `created_by` | User identifier, server-owned |
| `created_at` | timestamp |
| `updated_at` | timestamp |

Constraints/rules:

- if `group_id` is present, the assignee has an active assignment to that Group when the task is created;
- TEACHER changes only the status of an own assigned task;
- assignee, title and other management fields cannot be changed through the TEACHER status endpoint.

### 2.11 `notifications`

| Field | Frozen definition |
|---|---|
| `id` | UUID identifier |
| `organization_id` | tenant identifier |
| `recipient_user_id` | User identifier |
| `kind` | notification kind |
| `entity_type` | referenced entity type |
| `entity_id` | nullable referenced entity identifier |
| `read_at` | nullable timestamp |
| `created_at` | timestamp |

Notification rows contain no duplicated free-text PII payload. Reads and read acknowledgement are recipient-scoped.

### 2.12 `document_notices`

| Field | Frozen definition |
|---|---|
| `id` | UUID identifier |
| `organization_id` | tenant identifier |
| `recipient_user_id` | User identifier |
| `title` | bounded text |
| `kind` | notice kind |
| `requires_ack` | boolean |
| `issued_by` | User identifier, server-owned |
| `acknowledged_at` | nullable timestamp |
| `created_at` | timestamp |

This table is notice/acknowledgement metadata only. It introduces no binary document storage.

### 2.13 `photo_consents`

| Field | Frozen definition |
|---|---|
| `id` | UUID identifier |
| `organization_id` | tenant identifier |
| `child_id` | Child identifier |
| `status` | `granted | withdrawn` |
| `scope` | exactly `group_photo_report` |
| `effective_from` | effective start |
| `effective_to` | nullable effective end |
| `recorded_by` | User identifier, server-owned |
| `created_at` | timestamp |
| `updated_at` | timestamp |

This is a technical consent-state registry, not a legal conclusion. The legal sufficiency, form and source of consent are real-pilot decisions.

### 2.14 `photo_assets`

| Field | Frozen definition |
|---|---|
| `id` | UUID identifier |
| `organization_id` | tenant identifier |
| `group_id` | Group identifier |
| `storage_key` | opaque storage reference |
| `mime_type` | validated MIME type |
| `size_bytes` | validated byte size |
| `captured_at` | nullable timestamp |
| `uploaded_by` | User identifier, server-owned |
| `status` | `active | restricted | removed` |
| `created_at` | timestamp |

No public object URL is stored.

### 2.15 `photo_asset_children`

| Field | Frozen definition |
|---|---|
| `organization_id` | tenant identifier |
| `photo_asset_id` | PhotoAsset identifier |
| `child_id` | Child identifier |

The teacher manually identifies each depicted child. There is no face recognition, biometric identification or automatic child recognition. Upload and read eligibility requires valid group access and active consent for every linked Child.

Consent withdrawal:

- immediately blocks new uploads for that Child;
- makes affected asset bytes inaccessible to ordinary TEACHER/PARENT reads;
- leaves physical deletion/retention to a separate legal/business decision;
- exposes to DIRECTOR only the administrative metadata needed to resolve the restricted asset.

## 3. Tenant and relational integrity

Every new row is tenant-scoped. All referenced User, Employee, Group, Child, Guardian, Poll, Thread, Task and asset entities must belong to the authenticated actor's tenant. The Backend validates cross-entity tenant consistency even where a relational database FK alone cannot express it. Client-supplied `organization_id`, actor, sender, author, recorder or recipient identity never selects scope.

## 4. Photo storage and content boundary

- Dev/test/preview: synthetic photos only; local/ephemeral adapter allowed.
- Production: upload is disabled/fail-closed until an approved provider, data location, access model, backup policy, retention policy and privacy/legal configuration exists.
- Files are delivered only through authenticated Backend authorization.
- No public storage URL.
- Strip EXIF/metadata before persistence where technically applicable.
- Enforce MIME/type and size allowlists.
- Never log photo bytes, object secrets or sensitive storage keys.
- No biometrics or face recognition.

An external production provider is not selected by Stage 6 design.

## 5. PII minimization and logging

- Dev/test/preview use synthetic data only; production data is never copied into those environments.
- Default roster contains only Child id and name fields needed by the screen.
- Guardian data is relationship-scoped and contact fields appear only when a specific contact screen needs them.
- No speculative PII, medical module or medical-only fields.
- Communication body, diary note, incident description and photo bytes never enter technical logs.
- Notification rows do not duplicate free-text PII.
- Document notices do not contain binary document content.
- Passwords, tokens, cookies and session data are never exposed through teacher-domain responses or audit details.

## 6. Audit contract

All security/business writes produce privacy-minimized `AuditEvent` entries. Required action families:

- `teacher_account.create/reset/block/unblock`
- `teacher_assignment.create/archive/restore`
- `schedule.create/update/archive`
- existing `attendance.create/update`
- `teacher_message.create`
- `diary.create/update`
- `teacher_announcement.create/update/archive`
- `poll.create/close/vote`
- `incident.create/update/resolve`
- `teacher_task.create/update/cancel/status`
- `notification.read`
- `document_notice.ack`
- `photo_consent.record/withdraw`
- `photo.create/restrict/remove`

`AuditEvent.details` contains identifiers, state transitions and changed-field names only. It must not copy:

- communication body;
- diary note;
- announcement body/title where the current audit policy excludes it;
- incident description;
- document content;
- photo bytes;
- a storage secret/key when that increases exposure;
- phone/email;
- passwords, tokens or cookies.

DIRECTOR-only Audit read remains unchanged.

## 7. Mandatory negative and regression tests

These cases are the minimum Stage 6 acceptance set.

### 7.1 Tenant

- TEACHER Garden A → any Garden B Group/Child/Guardian/Thread/Diary/Poll/Incident/Task/Photo: non-disclosing denial.
- Forged `organization_id` never changes tenant.

### 7.2 Assignment

- TEACHER assigned Group A → Group B direct UUID: denial.
- Archived assignment: access denied immediately on the next request.
- Archived Group: teacher group access denied.
- TEACHER with zero assignments: login allowed and cabinet empty.
- Foreign assignment cannot be created.

### 7.3 Identity and lifecycle

- TEACHER User without an active linked Employee: denied.
- Archived Employee: account blocked, sessions revoked and teacher access denied.
- Blocked TEACHER: denied.
- ADMIN account is not treated as TEACHER merely because its Employee has an assignment.

### 7.4 Existing management protection

- TEACHER → existing `/employees` management: `403`.
- TEACHER → existing `/groups` management writes: `403`.
- TEACHER → `/audit`: `403`.
- TEACHER cannot create/reset/block DIRECTOR or ADMIN accounts.
- ADMIN cannot create a TEACHER account or assignment.

### 7.5 Children and guardians

- Assigned teacher cannot see a Guardian of an unrelated Child.
- Transferred Child loses old teacher access on the next request.
- Archived Child is not writable through teacher attendance/diary.
- Direct thread with unrelated Guardian is rejected.

### 7.6 Attendance

- Teacher cannot write another Group.
- Teacher cannot bypass Group restriction through an existing Attendance record UUID.
- Existing DIRECTOR/ADMIN attendance behavior remains green.

### 7.7 Communication

- Client-supplied `sender_user_id` is ignored or forbidden according to the endpoint schema and never used as authority.
- Cross-thread access is denied.
- Direct-thread participants are derived server-side.
- Former teacher loses thread access after assignment removal.
- PARENT loses thread access when the active Child relation no longer qualifies.
- Messages remain immutable.

### 7.8 Announcements

- TEACHER cannot publish an all-garden announcement.
- TEACHER cannot target an unassigned Group.
- TEACHER cannot mutate an unauthorized teacher/director announcement.

### 7.9 Polls

- PARENT cannot vote outside an eligible Group.
- Duplicate vote is rejected.
- Foreign Option/Poll mismatch is rejected.

### 7.10 Diary, incidents and tasks

- Teacher cannot write Child diary outside assignment.
- Teacher cannot read/update a foreign task.
- Teacher cannot change task assignee/title through the status endpoint.
- Incident rejects medical-only fields.

### 7.11 Photos

- Missing consent: upload denied.
- Withdrawn or expired consent: upload denied.
- One non-consenting Child in a multi-child photo: entire upload denied.
- User cannot retrieve content after losing assignment/relation.
- Withdrawn consent restricts ordinary reads of the affected asset.
- No public object URL is stored or returned.
- Production upload fails closed until approved storage configuration exists.
- EXIF stripping and file type/size validation are tested.

### 7.12 Regression

- Existing DIRECTOR paths remain green.
- Existing ADMIN paths remain green.
- Existing PARENT Stage 1–5 behavior remains green.
- All Stage 5 required CI gates remain required.

## 8. Legal boundary

The schema and tests implement technical controls only. They do not prove full compliance with Federal Law No. 152-FZ or authorize a real pilot. Operator/controller/processor roles, hosting and data location, subprocessors and data flows, business retention/destruction, production backup protection, access administration and the legal sufficiency of photo consent remain separate decisions.
