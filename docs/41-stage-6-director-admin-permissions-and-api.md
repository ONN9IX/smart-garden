# Stage 6 — DIRECTOR / ADMIN Permissions and API Contract

**Status:** design proposal for Issue #123; frozen only after PR merge.
**Owner:** ONN9IX.
**All routes:** under `/api/v1`.

## 1. Authorization invariants

- authenticated User is the only source of actor identity, role and organization_id;
- client cannot select or override tenant, actor, sender or audit actor;
- frontend visibility is not authorization;
- TEACHER is never added to existing DIRECTOR/ADMIN management permissions as a shortcut;
- foreign-tenant resources use non-disclosing denial, normally 404 where existence must be hidden;
- known wrong-role access to a management surface returns 403;
- DIRECTOR is not platform Super Admin;
- ADMIN cannot elevate privileges.

## 2. Permission matrix

| Capability | DIRECTOR | ADMIN | TEACHER | PARENT |
|---|---|---|---|---|
| Management Dashboard | YES | YES | NO | NO |
| Manage Groups | YES | YES | NO | NO |
| Manage Children | YES | YES | NO | NO |
| Manage Guardians | YES | YES | NO | NO |
| Manage ChildGuardian relations | YES | YES | NO | NO |
| Manage PARENT accounts | YES | YES | NO | NO |
| Manage Employee cards | YES | YES under frozen lifecycle rules | NO | NO |
| Manage ADMIN accounts | YES | NO | NO | NO |
| Manage TEACHER accounts | YES | NO | NO | NO |
| Read TEACHER assignments | YES | YES | own context only | NO |
| Write TEACHER assignments | YES | NO | NO | NO |
| Attendance all Groups | YES | YES | assigned only | NO |
| Schedule read | YES | YES | assigned only | eligible read where exposed |
| Schedule manage | YES | YES | NO | NO |
| All-garden Announcement | YES | YES | NO | read eligible |
| Group Announcement management | YES | YES | own+assigned only | read eligible |
| Canonical Group chat | YES | YES | assigned | eligible |
| Direct TEACHER↔PARENT thread | NO blanket content | NO blanket content | participant | participant |
| Diary | read all same-tenant | operational read | assigned read/write | linked Child read |
| Poll create/close | YES | YES | assigned Group | NO |
| Poll vote | NO | NO | NO | eligible only |
| Incident management | YES | YES | assigned Group | no raw record |
| Teacher Task management | YES | YES | own status only | NO |
| Own Notifications | YES | YES | YES | YES |
| Document Notices | issue/list to TEACHER | issue/list to TEACHER | own/ack | deferred in this Core |
| Photo-consent technical state | YES | YES | read assigned state only | NO write |
| Photo content | no blanket access | no blanket access | assigned+consent | linked+consent |
| Audit read | YES | NO | NO | NO |
| Organization settings | YES | NO | NO | NO |

## 3. Existing Stage 1–5 APIs — reuse unchanged

### Auth

- POST /auth/login
- GET /auth/me
- POST /auth/change-password
- POST /auth/logout

### Groups

- GET /groups
- POST /groups
- GET /groups/{group_id}
- PATCH /groups/{group_id}
- POST /groups/{group_id}/archive
- POST /groups/{group_id}/restore

DIRECTOR/ADMIN only.

### Children

- GET /children
- POST /children
- GET /children/{child_id}
- PATCH /children/{child_id}
- POST /children/{child_id}/archive
- POST /children/{child_id}/restore
- existing ChildGuardian relation endpoints

Child transfer remains PATCH /children/{child_id} with group_id. Do not add a duplicate transfer endpoint.

### Guardians

- existing /guardians CRUD/archive/restore
- existing PARENT account create/reset/block/unblock routes

Frozen PARENT account behavior remains:

- DIRECTOR: allowed
- ADMIN: allowed

### Employees

- existing /employees CRUD/archive/restore
- existing /employees/{employee_id}/account* remain ADMIN-account lifecycle endpoints

ADMIN-account management remains DIRECTOR-only.

Do not turn existing account endpoint into a role-selection API.

### Attendance

Use existing /attendance management API.

### Announcements

Use existing /announcements management API.

### Dashboard

GET /dashboard/summary remains unchanged.

### Audit

- GET /audit
- GET /audit/{event_id}

DIRECTOR-only.

## 4. No duplicate API families

Do not create:

- /management/groups
- /management/children
- /management/guardians
- /management/employees
- /management/attendance
- /management/announcements

Rule:

`existing capability -> reuse`

`new capability -> additive endpoint`

## 5. TEACHER account management

Use the Stage 6 frozen family:

DIRECTOR-only writes:

- POST /teacher-management/employees/{employee_id}/account
- POST /teacher-management/employees/{employee_id}/account/reset-password
- POST /teacher-management/employees/{employee_id}/account/block
- POST /teacher-management/employees/{employee_id}/account/unblock

Backend owns:

- role=TEACHER;
- tenant;
- account status transition;
- temporary credential generation;
- audit actor.

ADMIN/TEACHER/PARENT: 403.

## 6. TEACHER assignments

Read:

- GET /teacher-management/assignments

DIRECTOR/ADMIN.

Expected filters:

- employee_id
- group_id
- status=active|archived|all

Writes, DIRECTOR-only:

- POST /teacher-management/assignments
- POST /teacher-management/assignments/{assignment_id}/archive
- POST /teacher-management/assignments/{assignment_id}/restore

Create payload contains only:

- employee_id
- group_id

Backend owns:

- organization_id
- assigned_by
- lifecycle status.

Validation:

- active same-tenant Employee;
- linked active TEACHER User;
- active same-tenant Group.

## 7. Teachers management projection

Add:

- GET /teacher-management/teachers
- GET /teacher-management/teachers/{employee_id}

DIRECTOR/ADMIN read.

This is a projection, not a new DB entity.

Source:

`Employee + linked User(role=TEACHER) + TeacherGroupAssignment`

List filters may include:

- status;
- account_status;
- group_id;
- q.

Safe response:

- Employee id/names/position/status;
- safe account summary: user_id, username, status, must_change_password;
- assigned Group ids/names.

Never return password/hash/session/secret.

## 8. Management Today

Add:

- GET /management/today

DIRECTOR/ADMIN.

This does not replace /dashboard/summary.

Response is privacy-minimized and may include:

- garden-local date;
- active_children;
- present;
- absent;
- unknown;
- active_groups;
- groups_without_active_teacher_assignment;
- active_employees;
- task counts;
- open incident count;
- unread own notification count;
- structured attention_items.

Attention item fields should be identifiers/enums/counts, not sensitive free text.

## 9. Management Notifications

Add:

- GET /management/notifications
- POST /management/notifications/{notification_id}/read

DIRECTOR/ADMIN, recipient-scoped.

Query may include:

- status=unread|read|all
- kind
- limit
- offset

Client cannot provide recipient_user_id or organization_id as authority.

## 10. Management Settings

Add:

- GET /management/settings
- PATCH /management/settings

DIRECTOR-only.

Response:

- organization.id
- organization.name
- organization.timezone

Writable:

- name
- timezone

Timezone must be valid IANA.

Never expose infrastructure/security configuration.

## 11. Schedule

Use Stage 6 frozen management family:

- GET /teacher-management/schedule?group_id=
- POST /teacher-management/schedule
- PATCH /teacher-management/schedule/{item_id}
- POST /teacher-management/schedule/{item_id}/archive

DIRECTOR/ADMIN.

Create/update fields:

- group_id
- weekday 0..6
- start_time
- end_time
- title

Backend owns tenant/actor/status. end_time > start_time.

## 12. Group communication management

Use:

- GET /teacher-management/communications/groups/{group_id}/messages
- POST /teacher-management/communications/groups/{group_id}/messages

DIRECTOR/ADMIN.

Only canonical same-tenant Group thread.

No management endpoint may provide blanket access to direct TEACHER↔PARENT content.

POST payload contains body only. Backend owns sender and tenant.

Messages are immutable; no edit/delete API.

## 13. Diary management read

Add:

- GET /teacher-management/diary
- GET /teacher-management/diary/{entry_id}

DIRECTOR/ADMIN, read-only.

List query:

- child_id required
- date_from optional
- date_to optional

Response may include:

- entry_id
- child_id
- group_id snapshot
- date
- author_user_id
- note
- timestamps

Note is business content but excluded from technical logs and Audit.details.

## 14. Poll management

Add:

- GET /teacher-management/polls
- GET /teacher-management/polls/{poll_id}
- POST /teacher-management/polls
- POST /teacher-management/polls/{poll_id}/close

DIRECTOR/ADMIN.

Create:

- group_id
- question
- options[]
- closes_at optional

Backend owns tenant/creator/status.

Normal management result is aggregate:

- option
- vote_count
- total_votes

No default full voter-identity list.

## 15. Incidents

Use frozen Stage 6 family:

- GET /teacher-management/incidents?group_id=&status=
- GET /teacher-management/incidents/{incident_id}
- POST /teacher-management/incidents
- PATCH /teacher-management/incidents/{incident_id}

DIRECTOR/ADMIN.

Additional filters may include category/date range if implementation remains compatible with the frozen data model.

No diagnosis/medication/treatment/medical-document fields.

## 16. Teacher Tasks

Use:

- GET /teacher-management/tasks
- POST /teacher-management/tasks
- PATCH /teacher-management/tasks/{task_id}
- POST /teacher-management/tasks/{task_id}/cancel

DIRECTOR/ADMIN.

Create fields:

- assignee_employee_id
- group_id optional
- title
- description optional
- due_at optional

If group_id is present, assignee must have active assignment to that Group when required by the frozen Stage 6 contract.

TEACHER write remains status-only through Track B.

## 17. Document Notices

Use:

- GET /teacher-management/document-notices
- POST /teacher-management/document-notices

DIRECTOR/ADMIN.

For this Management Core, the requested target must resolve to an active same-tenant TEACHER User.

Create request identifies the intended target and notice metadata:

- recipient_user_id
- title
- kind
- requires_ack

Backend resolves and validates the target TEACHER and stores the authoritative recipient, tenant and issue actor. A client-supplied recipient identifier is a target selector, not authority to cross tenant or role boundaries.

No binary/file/evidence content accepted.

PARENT delivery is deferred unless separately frozen later.

## 18. Photo consent registry

Use:

- GET /teacher-management/photo-consents
- POST /teacher-management/photo-consents
- POST /teacher-management/photo-consents/{consent_id}/withdraw

DIRECTOR/ADMIN.

TEACHER/PARENT writes: 403.

Technical registry only; no evidence blob.

## 19. Payload ownership

Backend-owned values include:

- organization_id;
- actor/sender/author;
- created_by/updated_by;
- assigned_by;
- account role;
- temporary credential generation;
- message sender;
- incident reporter/resolver;
- consent recorder;
- authoritative Document Notice recipient after same-tenant TEACHER resolution;
- audit actor.

Client-supplied server-owned fields should be forbidden unless an existing frozen endpoint explicitly defines otherwise.

## 20. Error semantics

- no/invalid session -> 401;
- wrong role on known management route -> 403;
- foreign tenant or hidden object -> 404;
- validation -> project-standard validation error;
- conflict -> 409 where applicable;
- unexpected failure -> safe 500.

Do not leak foreign-tenant existence in error messages.

## 21. Mandatory permission tests

At minimum:

- ADMIN -> /audit = 403;
- ADMIN -> TEACHER account write = 403;
- ADMIN -> assignment write = 403;
- ADMIN -> settings write = 403;
- TEACHER -> existing management APIs = 403;
- PARENT -> management APIs = 403;
- cross-tenant Group/Child/Guardian/Employee/Task/Incident/Poll/Diary/AuditEvent hidden;
- forged organization_id rejected/ignored only according to frozen schema, never authoritative;
- DIRECTOR/ADMIN arbitrary direct TEACHER↔PARENT thread access denied;
- user cannot read/mark another user's Notification;
- Child transfer to foreign/archived Group denied;
- old TEACHER loses Child access after transfer;
- PARENT account DIRECTOR+ADMIN regression preserved;
- ADMIN account DIRECTOR-only regression preserved;
- TEACHER account DIRECTOR-only enforced.

## 22. API freeze rule

After this design merges, implementation must not independently:

- rename frozen routes;
- widen role permissions;
- add TEACHER to old management routes;
- add client-controlled tenant;
- create duplicate management API families;
- change direct-message privacy;
- change Stage 1–5 semantics.

Such need triggers STOP -> Master Chat.
