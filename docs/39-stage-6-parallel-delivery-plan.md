# Stage 6 — parallel delivery plan

**Status:** design-frozen by Issue #121.

**Owner of this design gate:** F1zname.

**PARALLEL-SAFE:** NO — this is a serialized design-only gate.

## 1. Required order

```text
Stage 6 Design
→ merge/freeze
→ S6-FOUNDATION
→ merge
→ post-merge CI green
→ parallel implementation
```

No ONN9IX/F1zname Stage 6 implementation starts before Foundation merges and its post-merge CI is green. From that fresh exact baseline, Master Chat creates one major autonomous `S6-TEACHER-CABINET` Issue for F1zname and any explicitly disjoint ONN9IX Track A Issues.

## 2. Design gate

Issue #121 freezes:

- TEACHER identity, lifecycle and assignment semantics;
- permission matrix and API;
- the complete teacher-domain schema for one later migration;
- privacy, photo/document boundaries and mandatory negative tests;
- Foundation ownership, reserved files, parallel lanes and merge rules.

This gate contains documentation only. It does not create application code, migrations, tests, CI changes, dependencies or implementation Issues.

## 3. S6-FOUNDATION — serialized

**Owner:** F1zname

**PARALLEL-SAFE:** NO

Foundation implements the shared contract exactly once:

### Backend shared work

- add `TEACHER` to the User role constraint and auth schemas;
- validate the active same-tenant Employee for TEACHER auth/session resolution;
- make Employee lifecycle compatible with TEACHER block/revoke behavior;
- create `TeacherGroupAssignment` and every teacher-domain model frozen in docs/38;
- create one Alembic migration containing the complete Stage 6 teacher schema;
- register models;
- add reusable teacher permission primitives;
- add teacher-management account/assignment primitives;
- register the teacher router aggregation boundary;
- add a synthetic teacher seed;
- add required Foundation tests;
- add a fail-closed photo-upload configuration boundary if implementation requires it.

### Frontend shared work

- add `TEACHER` to the auth Role;
- make AuthGate aware of the teacher route;
- make AppShell a stable role-aware shell;
- split DIRECTOR/ADMIN and TEACHER navigation into separate owned modules;
- optionally add only the teacher route skeleton/empty state;
- add synthetic login/browser Foundation coverage.

Foundation preserves all existing DIRECTOR/ADMIN/PARENT behavior. It must merge and complete post-merge CI before either parallel lane begins.

Foundation is the one and only mandatory intermediate Master Chat implementation checkpoint before autonomous TEACHER cabinet delivery.

## 4. Reserved after Foundation

After Foundation merges, the following shared/high-conflict files and areas are reserved. Neither track edits them without `STOP → Master Chat → serialize/rebaseline`:

- `backend/app/models/user.py`
- `backend/app/models/employee.py`
- `backend/app/models/group.py`
- `backend/app/models/__init__.py`
- `backend/app/services/auth.py`
- `backend/app/services/employees.py`
- `backend/app/services/employee_accounts.py`
- `backend/app/core/permissions.py`
- `backend/app/main.py`
- Alembic migration head/files
- `frontend/src/types/auth.ts`
- `frontend/src/features/auth/auth-gate.tsx`
- `frontend/src/components/layout/app-shell.tsx`
- shared frontend API client (`frontend/src/lib/api/client.ts`)
- `.github/workflows/ci.yml`
- `AGENTS.md`
- `docs/CURRENT_STATE.md`
- root `README.md`

The same STOP rule applies to any shared auth, model, migration, AppShell, CI or current-state file not safely isolated by the exact active Issue write-sets.

## 5. Track A — ONN9IX — DIRECTOR / ADMIN

**Owner:** ONN9IX

Purpose: DIRECTOR/ADMIN enhancements and management surfaces approved by separate exact Issues. Examples:

- teacher-management UI;
- assignment UI;
- schedule/task management UI;
- DIRECTOR/ADMIN fields and operational enhancements explicitly approved in their Issues.

Track A owns its DIRECTOR/ADMIN-specific files and new management modules. It must not edit TEACHER-owned modules. Master Chat creates separate Track A Issues from the Foundation post-merge baseline; each requires:

- exact scope;
- exact baseline;
- exact write-set;
- no overlap with an active F1zname Issue;
- explicit `PARALLEL-SAFE` evaluation.

Do not create one giant unspecified DIRECTOR/ADMIN branch. Finance, payments and binary-document architecture are not frozen by this TEACHER design and require their own explicit design/Issue.

## 6. Track B — F1zname — TEACHER

**Owner:** F1zname

Exclusive implementation namespaces are used so Track B avoids Track A and reserved files.

### Backend

- `app/api/teacher/**`
- `app/schemas/teacher/**`
- `app/services/teacher/**`
- teacher-specific tests

### Frontend

- `src/app/teacher/**`
- `src/features/teacher/**`
- `src/lib/api/teacher/**`
- Stage 6 teacher types
- TEACHER browser specs

PARENT-facing communication/diary/poll/photo additions may be in Track B only where the exact Issue write-set does not overlap Track A or a reserved file.

Track B is delivered as one major Issue, one branch and one PR for the complete TEACHER cabinet. Groups, Attendance, Communications, Diary, Polls, Incidents, Tasks, Photos and other teacher modules are internal implementation milestones, not separate Master Chat approval gates.

## 7. Planned implementation Issues

No implementation Issue is created or started by this design gate. Master Chat creates the following Issues only after the required preceding merge and establishes the exact baseline/write-set.

### S6-FOUNDATION

- Owner: F1zname
- `PARALLEL-SAFE: NO`
- Goal: TEACHER role, Employee lifecycle, complete teacher schema in one migration, assignment access primitive, teacher-management account/assignment backend, shared frontend auth/navigation split, synthetic seed and Foundation tests.

### S6-TEACHER-CABINET — autonomous full delivery

- Owner: F1zname
- `PARALLEL-SAFE: YES` only with explicitly approved, disjoint ONN9IX Track A work after Foundation.
- Delivery: one major Issue, one branch and one PR.
- Scope: complete TEACHER cabinet — shell/navigation, Today, assigned Groups/roster/guardian context, Attendance, Schedule read, Group and direct communication, Diary, Group announcements, Polls, Incidents, Tasks, Notifications, document notice acknowledgement, photo-consent behavior, authenticated synthetic photo boundary, mandatory negative/security tests, TEACHER browser E2E and relevant regression.

F1zname may use as many commits and internal milestones as needed. There is no intermediate Master Chat approval after Groups, Attendance, Communications, Diary, Polls, Incidents, Tasks, Photos or another cabinet module. Ordinary implementation defects are fixed in the same branch.

F1zname returns to Master Chat early only if implementation would require:

- changing a frozen Stage 6 architecture, API or data-model decision;
- changing auth/session semantics, tenant isolation or the permission/RBAC boundary;
- changing Stages 1–5 behavior beyond an explicitly additive Stage 6 contract;
- editing a reserved shared file outside the exact Issue write-set;
- creating another Alembic migration/head after Foundation;
- introducing a new database, Backend or auth stack;
- introducing real PII in dev/test/preview;
- introducing medical data, biometrics or face recognition;
- selecting or connecting an external production photo/file provider;
- resolving an intentionally open legal/privacy/retention/hosting decision;
- overlapping an active ONN9IX Track A write-set.

At completion F1zname returns one full handoff for the complete cabinet. Master Chat performs one full-product review, not module-by-module reviews.

### ONN9IX DIRECTOR/ADMIN Issues

Created separately by Master Chat from the Foundation post-merge baseline with explicit, disjoint write-sets and `PARALLEL-SAFE` decisions.

### S6-ACCEPTANCE

- Owner: chosen by Master Chat after implementation.
- `PARALLEL-SAFE: NO`.
- Goal: review the complete TEACHER cabinet as one product, with full DIRECTOR/ADMIN/PARENT regression, TEACHER E2E, all tenant/permission/participant/privacy negative tests, preserved Stage 5 CI/security/recovery gates, privacy review, confirmation of no real PII and Stage 6 technical acceptance/freeze.

## 8. Migration lane

- Foundation owns one migration containing the complete teacher-domain schema.
- Neither Track A nor Track B creates an independent Alembic head during parallel work.
- If a later DIRECTOR/ADMIN or TEACHER feature requires a migration, Master Chat serializes that migration lane.
- After the migration PR merges and post-merge CI is green, dependent work is rebaselined on the refreshed exact `main` SHA.

## 9. Parallel-safe rule

Parallel work is allowed only when all conditions hold:

1. Foundation is merged;
2. Foundation post-merge CI is green;
3. Master Chat created each active Issue from a fresh exact baseline;
4. every active Issue is explicitly marked `PARALLEL-SAFE: YES`;
5. write-sets are exact and disjoint;
6. neither track edits a reserved shared file;
7. no architecture/API/DB/auth/RBAC/tenant/privacy conflict exists.

Any need to edit a reserved shared file during parallel work triggers:

```text
STOP
→ Master Chat
→ rebaseline / serialize
```

## 10. Merge and rebaseline rules

- one Issue → one branch → one PR;
- no developer self-merge;
- Foundation first;
- Track A and the single S6-TEACHER-CABINET Issue start only after Foundation post-merge CI is green;
- parallel PRs merge only while their write-sets remain disjoint;
- after any shared or migration merge, Master Chat establishes a fresh exact main baseline before dependent work;
- F1zname needs no intermediate Master Chat approval between internal TEACHER modules;
- ordinary TEACHER defects remain in the same S6-TEACHER-CABINET branch;
- architecture/API/DB/auth/RBAC/tenant/security/privacy/shared-file conflicts trigger the explicit STOP rule and return to Master Chat;
- the complete cabinet returns once for full-product review unless a STOP condition occurs earlier;
- every required PR CI must be fully green before review/merge decision.

## 11. Acceptance gate

`S6-ACCEPTANCE` is serialized and runs only after the complete S6-TEACHER-CABINET delivery and required Track A dependencies are merged. It reviews the cabinet as one product, not as internal teacher sub-issues. Acceptance must verify:

- TEACHER end-to-end behavior;
- all frozen negative tenant, assignment, identity, participant and photo cases;
- no weakening of DIRECTOR/ADMIN/PARENT behavior;
- all Stage 5 required CI/security/recovery gates;
- synthetic-only dev/test/preview data;
- privacy boundaries and no real PII;
- production photo upload remains fail-closed without approved configuration;
- technical acceptance is not presented as full 152-FZ compliance or authorization for a real pilot.
