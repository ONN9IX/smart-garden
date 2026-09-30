# Stage 6 — permissions and API contract

**Status:** design-frozen by Issue #121; no endpoint in this document is implemented by the design Issue.

All routes are under `/api/v1`. Authorization and tenant enforcement are Backend responsibilities.

## 1. Authorization invariants

- The authenticated `User` is the only source of actor identity, role and `organization_id`.
- A client cannot select or override tenant, actor, sender or thread participants.
- Every TEACHER group operation revalidates the active User, active same-tenant Employee, active assignment and active Group on the current request.
- Frontend route or navigation visibility is not authorization.
- TEACHER is not added to existing DIRECTOR/ADMIN management permissions.
- Foreign-tenant and unassigned resources receive non-disclosing denial; use `404` where resource existence must be hidden.
- Role denial on a known management surface remains `403`.
- Assignment removal or child transfer takes effect on the next request without requiring session revocation.

## 2. Permission matrix

### 2.1 Existing management

| Capability | DIRECTOR | ADMIN | TEACHER | PARENT |
|---|---|---|---|---|
| Manage all groups | YES | YES | NO | NO |
| Manage all children | YES | YES | NO | NO |
| Manage guardians | YES | YES | NO | NO |
| Manage employees | YES | YES under frozen rules | NO | NO |
| Read Audit | YES | NO | NO | NO |
| Create TEACHER account | YES | NO | NO | NO |
| Assign/unassign TEACHER to Group | YES | NO | NO | NO |
| Block/reset TEACHER account | YES | NO | NO | NO |

### 2.2 Teacher operational domains

| Capability | DIRECTOR | ADMIN | TEACHER | PARENT |
|---|---|---|---|---|
| Teacher Today | N/A | N/A | own context | NO |
| Read assigned group roster | all | all | assigned only | linked children only |
| Attendance write | all | all | assigned groups only | NO |
| Schedule read | all | all | assigned groups only | linked child/group read when exposed |
| Schedule manage | YES | YES | NO | NO |
| Group announcements manage | all | all | assigned group only | read eligible |
| All-garden announcement | YES | YES | NO | read eligible |
| Group chat | operational read/manage | operational read/manage | assigned groups | eligible child group |
| Direct TEACHER↔PARENT thread | NO blanket content access | NO blanket content access | eligible assigned child/guardian only | own guardian relation only |
| Child diary | read all | operational read | assigned child write/read | linked child read |
| Poll create/close | all | all | assigned groups | NO |
| Poll vote | NO | NO | NO | eligible group only |
| Incident create/update | read/manage all | operational read/manage | assigned group only | NO direct incident record in Stage 6 |
| Teacher task create/assign | YES | YES | NO | NO |
| Teacher task status | all | all | own assigned tasks | NO |
| Notifications | own/admin context | own/admin context | own | own |
| Document notices | manage/issue per Track A | manage/issue per Track A | own/ack | own if later exposed |
| Photos | admin oversight | no broad grant by default | assigned group + consent gate | linked child + consent gate |

Direct-message content is participant-scoped. DIRECTOR and ADMIN do not receive blanket access to it. Audit records message metadata, not message body.

## 3. Teacher identity and group context

| Method and route | Access | Frozen behavior |
|---|---|---|
| `GET /teacher/today` | TEACHER own context | Aggregator implemented only after dependencies exist; returns assigned groups, today's schedule, attendance summary, active own tasks, own notifications and unread eligible communication counts. |
| `GET /teacher/groups` | TEACHER | Active assigned groups only; zero assignments returns an empty list. |
| `GET /teacher/groups/{group_id}` | TEACHER assigned group | Revalidates assignment and active Group. |
| `GET /teacher/groups/{group_id}/children` | TEACHER assigned group | Minimal active roster only. |
| `GET /teacher/groups/{group_id}/guardians` | TEACHER assigned group | Only guardians with an active relation to an eligible child; minimized contact fields. |

Every group route uses the frozen teacher-group access primitive. No request accepts `organization_id`.

## 4. Attendance

| Method and route | Access | Frozen behavior |
|---|---|---|
| `GET /teacher/attendance?date=&group_id=` | TEACHER assigned group | Reads eligible children/records only. |
| `POST /teacher/attendance` | TEACHER assigned group | Creates/upserts through the existing `Attendance` model for an active child in an assigned active Group. |
| `PATCH /teacher/attendance/{record_id}` | TEACHER assigned group | Record UUID cannot bypass current group access. |

No second attendance table is created. The Backend derives tenant and actor and preserves the existing historical Group snapshot on Attendance.

## 5. Schedule

### Teacher

- `GET /teacher/schedule?group_id=` — TEACHER reads only an actively assigned Group.

### Management

- `GET /teacher-management/schedule?group_id=`
- `POST /teacher-management/schedule`
- `PATCH /teacher-management/schedule/{item_id}`
- `POST /teacher-management/schedule/{item_id}/archive`

DIRECTOR and ADMIN manage schedule under tenant scope. TEACHER has no schedule-write permission. Schedule does not infer attendance.

## 6. Teacher account and assignments

### DIRECTOR-only writes

- `POST /teacher-management/employees/{employee_id}/account`
- `POST /teacher-management/employees/{employee_id}/account/reset-password`
- `POST /teacher-management/employees/{employee_id}/account/block`
- `POST /teacher-management/employees/{employee_id}/account/unblock`
- `POST /teacher-management/assignments`
- `POST /teacher-management/assignments/{assignment_id}/archive`
- `POST /teacher-management/assignments/{assignment_id}/restore`

### DIRECTOR/ADMIN read

- `GET /teacher-management/assignments`

Account and assignment write payloads identify target Employee/Group only. The Backend owns tenant, role, status transitions, credential generation, `assigned_by` and audit actor. ADMIN cannot create, reset, block or unblock a TEACHER account and cannot create/archive/restore an assignment.

Existing ADMIN employee-account endpoints keep their Stage 1–5 semantics.

## 7. Communication

### Teacher

- `GET /teacher/communications/threads`
- `GET /teacher/communications/threads/{thread_id}/messages`
- `POST /teacher/communications/threads/{thread_id}/messages`
- `POST /teacher/communications/direct`
- `GET /teacher/groups/{group_id}/communication-thread`

### Parent

- corresponding `/parent/communications/*` endpoints for an eligible linked-child/group context.

Direct-thread creation validates server-side:

1. the teacher has an active assignment;
2. the child is active and belongs to the assigned active Group;
3. the guardian has an active same-tenant `ChildGuardian` relation to the child;
4. the guardian's PARENT User is active.

Group membership is derived from current assignments and child relations. A payload never supplies a participant list. `sender_user_id` and `organization_id` are server-owned. Messages are immutable: no user edit and no user delete.

## 8. Diary

### Teacher

- `GET /teacher/diary?child_id=&date_from=&date_to=`
- `POST /teacher/diary`
- `PATCH /teacher/diary/{entry_id}`

### Parent

- `GET /parent/children/{child_id}/diary`

TEACHER read/write requires a current assignment to the child's active Group. PARENT read requires an active linked-child relation. Tenant, author and group snapshot are server-owned.

## 9. Announcements

### Teacher

- `GET /teacher/announcements?group_id=`
- `POST /teacher/announcements`
- `PATCH /teacher/announcements/{announcement_id}`
- `POST /teacher/announcements/{announcement_id}/archive`

The create payload contains only `group_id`, `title` and `body`. Backend always sets `target_type=group`, tenant and actor. TEACHER cannot publish `target_type=all` and can update/archive only an eligible assigned-group announcement under the frozen Stage 6 author/permission rule.

The existing `Announcement` table and existing DIRECTOR/ADMIN announcement API remain unchanged.

## 10. Polls

### Teacher

- `GET /teacher/polls?group_id=`
- `POST /teacher/polls`
- `POST /teacher/polls/{poll_id}/close`

### Parent

- `GET /parent/polls`
- `POST /parent/polls/{poll_id}/vote`

TEACHER operates assigned-group polls only. PARENT votes only in an eligible Group. Stage 6 permits one non-anonymous, single-option vote per PARENT User per poll; no cross-group voting.

## 11. Incidents

### Teacher

- `GET /teacher/incidents?group_id=&status=`
- `POST /teacher/incidents`
- `PATCH /teacher/incidents/{incident_id}`

### Management

- separate DIRECTOR/ADMIN operational read/manage endpoints under `/teacher-management/incidents`.

TEACHER access is assigned-group only. The payload accepts no diagnosis, medication, medical document or treatment fields. PARENT does not receive the raw Incident record in Stage 6.

## 12. Tasks

### Teacher

- `GET /teacher/tasks`
- `PATCH /teacher/tasks/{task_id}` — status only for the authenticated teacher's own assigned task.

### Management

- `GET /teacher-management/tasks`
- `POST /teacher-management/tasks`
- `PATCH /teacher-management/tasks/{task_id}`
- `POST /teacher-management/tasks/{task_id}/cancel`

TEACHER cannot change assignee, title, description, due date or Group through the status endpoint. If a management create payload includes `group_id`, the assignee must have an active assignment to that Group at creation time.

## 13. Notifications and document notices

### Teacher

- `GET /teacher/notifications`
- `POST /teacher/notifications/{id}/read`
- `GET /teacher/document-notices`
- `POST /teacher/document-notices/{id}/ack`

All results are recipient-scoped. Recipient, tenant, issue actor and acknowledgement actor are server-owned. The teacher document endpoints do not upload, store or expose binary documents.

## 14. Photos

### Teacher

- `GET /teacher/photo-consents?group_id=`
- `POST /teacher/photos`
- `GET /teacher/photos?group_id=`
- `GET /teacher/photos/{photo_id}/content`

### Parent

- `GET /parent/photos?child_id=`
- `GET /parent/photos/{photo_id}/content`

The upload request identifies only `group_id`, `child_ids` and `file`. The server validates:

- active TEACHER assignment to the active same-tenant Group;
- every child is active and currently belongs to that Group;
- active consent for every linked child;
- MIME/type, size and metadata constraints.

No public object URL is returned. Content is streamed through authenticated Backend authorization. Production upload fails closed until approved storage/data-location/access/backup/retention/privacy configuration exists.

## 15. Response minimization

Default TEACHER roster response contains only:

- child id;
- first name;
- last name;
- middle name when present.

Birth date is not returned in every list and may appear only in a child-detail operation when a concrete Stage 6 UI requirement establishes necessity.

Guardian communication context may contain only:

- guardian id;
- first/last/middle name;
- `relation_type`;
- phone/email only when the specific contact screen requires it and a value exists.

Never expose to TEACHER:

- unrelated guardians or children;
- the full employee directory;
- account/security, password or session data;
- Audit;
- another Group or tenant;
- speculative medical data.

## 16. Payload ownership

| Value | Owner |
|---|---|
| `organization_id` | Backend from authenticated User |
| actor/sender/author/recorder | Backend from authenticated User |
| thread participants | Backend from current assignment and ChildGuardian relations |
| assignment `assigned_by` | Backend from DIRECTOR actor |
| account role/status and temporary credentials | Backend lifecycle service |
| announcement `target_type` for TEACHER | Backend, always `group` |
| diary historical/current-at-write `group_id` snapshot | Backend after current access validation |
| notification recipient | Backend business operation |
| photo `storage_key` and content delivery | Backend/storage abstraction; never a public URL |

Unknown or forbidden extra fields are rejected; client-supplied identity fields are ignored only where the frozen endpoint explicitly permits that behavior, otherwise they are forbidden.

## 17. Error and non-disclosure behavior

- Foreign tenant, unassigned Group, unauthorized child/guardian/thread/record/photo UUID: non-disclosing denial (`404` where existence must be hidden).
- TEACHER calling existing `/employees`, Group management writes or `/audit`: `403`.
- ADMIN attempting TEACHER account or assignment writes: `403`.
- Archived/blocked identity or missing active Employee link: access denied according to the auth lifecycle contract.
- Invalid cross-entity combinations, such as option/poll mismatch or unrelated direct-thread guardian: rejected without leaking foreign resource details.
- Production photo upload without approved configuration: fail-closed response; no fallback to public or unapproved storage.

## 18. Regression contract

- Existing DIRECTOR paths and permissions remain green.
- Existing ADMIN paths and frozen restrictions remain green.
- Existing PARENT Stage 1–5 behavior remains green.
- DIRECTOR-only Audit read remains frozen.
- Existing employee ADMIN-account routes retain their existing semantics.
- Existing Attendance and Announcement behavior remains the base contract.
- All Stage 5 required CI/security/recovery gates remain required.
