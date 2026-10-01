# Stage 9 — Entrance Kiosk Delivery Plan

**Status:** design proposal for Issue #142; frozen only after the design PR merges.
**Owner:** ONN9IX.
**Design baseline:** `4993d3e1f3128b8a1f23c7d7c085084b062fc6b8`.

## 1. Required gate

No Stage 9 runtime implementation starts before:

1. Issue #131 is merged;
2. Stage 6 post-merge CI is green;
3. Stage 6 integrated acceptance is complete;
4. Stage 6 is explicitly frozen;
5. current `main` exact SHA is recorded.

Stage 9 design may merge earlier because it is docs-only and disjoint from #131.

## 2. Design gate

Issue #142 owns exactly:

- `docs/52-stage-9-entry-kiosk-product-spec.md`
- `docs/53-stage-9-entry-kiosk-permissions-and-api.md`
- `docs/54-stage-9-entry-kiosk-data-privacy.md`
- `docs/55-stage-9-entry-kiosk-delivery-plan.md`

No code, migration, tests, CI, dependencies or shared coordination files.

## 3. Implementation objective

After Stage 6 freeze, deliver one provider-free entrance kiosk that:

- reuses canonical Attendance;
- works for DIRECTOR/ADMIN and assigned TEACHER;
- has no PARENT writes;
- uses server-derived garden-local date/time;
- has idempotent Arrival/Departure;
- persists no roster/attendance locally;
- has inactivity logout;
- remains online-only;
- has no biometrics or door control.

## 4. Implementation preflight

Master Chat inspects fresh post-Stage-6 main and only the relevant files:

- Attendance API/service/schema/tests;
- Organization timezone helper;
- Stage 6 TEACHER assignment permission helper;
- shared backend router extension points;
- frontend protected-route/AppShell extension points;
- auth logout/session behavior;
- current Audit contract;
- current CI.

Preflight verifies:

1. no Attendance schema migration is required;
2. kiosk can reuse current Attendance data;
3. server-side current local time can be produced without changing Organization schema;
4. existing TEACHER assignment helper can be reused;
5. an isolated `entry-kiosk` router can be registered without conflict;
6. an isolated frontend route can be added without auth redesign.

## 5. Expected schema decision

**No Stage 9 core migration.**

Stage 9 core must not create:

- device table;
- access-event table;
- kiosk-session table;
- offline queue;
- pickup-person table.

If implementation proves a new persisted entity is necessary, STOP and return to Master Chat for a separate serialized design/migration gate.

## 6. Optional minimal shared integration gate

If post-Stage-6 main lacks an owned router/navigation extension point, create one small serialized Issue before product work:

`S9-ENTRY-KIOSK-INTEGRATION`

Allowed purpose only:

- register isolated backend kiosk router and/or
- expose an existing role-aware frontend navigation extension.

No product logic, migration or auth redesign.

If no shared edit is required, skip this gate.

## 7. Primary implementation Issue

Create one major Issue:

`S9-ENTRY-KIOSK — staff entrance tablet over canonical Attendance`

Preferred delivery:

- one Issue;
- one fresh branch;
- one PR;
- ordinary defects fixed in the same branch;
- no module-by-module Master Chat gates.

## 8. Preferred isolated namespaces

Exact write-set is frozen from fresh main during preflight.

Preferred shape if compatible:

### Backend

- `backend/app/api/entry_kiosk/**`
- `backend/app/schemas/entry_kiosk/**`
- `backend/app/services/entry_kiosk/**`
- Stage 9-specific tests

Reuse existing:

- Attendance service/model;
- Organization timezone;
- TEACHER assignment permissions;
- Audit writer.

### Frontend

- `frontend/src/app/entry-kiosk/**`
- `frontend/src/features/entry-kiosk/**`
- `frontend/src/lib/api/entry-kiosk/**`
- `frontend/src/types/entry-kiosk/**`
- Stage 9 browser spec

Do not create a second auth/API client.

## 9. Internal implementation order

Recommended internal milestones:

1. authorization/scoping helper;
2. authorized Group list;
3. minimal current-day roster;
4. server-local clock helper usage;
5. Arrival command;
6. Departure command;
7. idempotency/concurrency handling;
8. privacy-safe Audit reuse;
9. frontend kiosk shell;
10. Group selector/roster;
11. transient in-memory search;
12. Arrival/Departure UX;
13. network/error/retry UX;
14. inactivity logout;
15. responsive tablet pass;
16. backend negative tests;
17. concurrency tests;
18. browser E2E;
19. frozen Attendance/Stage 6 regression;
20. full required CI.

## 10. Authorization implementation

Use existing auth/session architecture.

Create one kiosk access policy that resolves:

### DIRECTOR / ADMIN

- same tenant;
- active Group.

### TEACHER

- active same-tenant User;
- active Employee;
- active TeacherGroupAssignment;
- active Group.

No PARENT write path.

Do not duplicate TEACHER assignment semantics if Stage 6 already exposes a reusable helper.

## 11. Server clock implementation

Add no date/time fields to Arrival/Departure request bodies.

Backend computes:

- organization-local date;
- organization-local local-time value.

Use the same validated IANA timezone source already used by Attendance.

Tests must freeze/monkeypatch clock deterministically rather than relying on wall-clock timing.

## 12. Arrival/Departure transactional implementation

Use transaction/row locking sufficient to guarantee the frozen state machine.

Required concurrency outcomes:

- two Arrival requests → one first timestamp, no overwrite;
- two Departure requests → one first timestamp, no overwrite;
- Arrival retry after unknown network outcome → current server state returned;
- no duplicate Attendance row.

Do not weaken the existing unique Child/date constraint.

## 13. Existing Attendance compatibility

After kiosk actions:

- management `GET /attendance` must return the same record;
- Stage 6 TEACHER Attendance must return the same record when assigned;
- historical Group snapshot behavior remains correct;
- later Stage 8 PARENT attendance read will observe the same record.

No synchronization job.

## 14. Corrections

Do not build historical correction into kiosk.

If staff tapped the wrong Child or a time needs manual correction:

- use existing authorized Attendance workflow;
- correction remains Audit-visible.

Stage 9 may show a short instruction/link to the normal Attendance screen for an authorized role, but does not duplicate its editor.

## 15. Frontend kiosk mode

Required states:

- login required;
- authorized Group selection;
- loading roster;
- connected;
- saving;
- saved Arrival;
- saved Departure;
- business conflict;
- network unavailable;
- timed-out/logged-out.

Never show a fake success during network uncertainty.

## 16. Inactivity implementation

Use one implementation-owned inactivity duration selected during preflight.

Activity reset examples:

- pointer/touch;
- keyboard;
- successful navigation/action.

Timeout performs:

- immediate UI state clear;
- normal server logout attempt;
- navigation to Login.

No PIN-only unlock.

## 17. Offline behavior

Do not add PWA offline mutation behavior for kiosk.

No service-worker background sync for Attendance.

No local durable queue.

The test suite should explicitly verify that failed writes do not create a client-side “saved” state.

## 18. Privacy validation

Before PR handoff inspect:

- response fields;
- browser storage;
- logs;
- Audit details;
- error messages;
- screenshots/fixtures.

Confirm no:

- Guardian contact;
- finance;
- diary/message;
- incident detail;
- photo;
- medical field;
- real PII fixture.

## 19. Required backend tests

### Happy path

- DIRECTOR Arrival/Departure;
- ADMIN Arrival/Departure;
- assigned TEACHER Arrival/Departure;
- management Attendance reads same record.

### Idempotency

- repeated Arrival preserves time;
- repeated Departure preserves time;
- concurrent duplicate actions preserve first state.

### State conflicts

- Departure before Arrival;
- Arrival after Departure;
- inactive Child;
- archived Group.

### Tenant/RBAC

- foreign Group/Child;
- PARENT denied;
- unassigned TEACHER denied;
- archived assignment denied;
- archived Employee denied.

### Time

- server-controlled date/time;
- Organization timezone respected;
- client cannot provide alternate date/time.

### Privacy

- minimized roster;
- no Guardian/contact fields;
- Audit excludes Child name/search;
- synthetic-only fixtures.

## 20. Required browser E2E

Minimum:

```text
DIRECTOR/ADMIN
→ login
→ kiosk
→ select Group
→ find Child
→ Arrival
→ verify server result
→ retry Arrival
→ Departure
→ retry Departure
→ logout
```

Also:

```text
TEACHER
→ login
→ kiosk
→ only assigned Group visible
→ Arrival/Departure works
→ unassigned Group inaccessible
```

And:

```text
PARENT
→ direct kiosk route denied
```

Network-failure scenario verifies no false success/offline queue.

## 21. Regression

Keep green:

- existing management Attendance;
- Stage 6 TEACHER Attendance;
- tenant isolation;
- Stage 5 security/backup/recovery;
- auth/session/logout;
- Audit;
- Organization timezone.

Do not weaken old tests.

## 22. Parallel delivery after Stage 6

Stage 9 has no dependency on Stage 7 financial schema or Stage 8 PARENT consolidation.

It may run in parallel with later product work only when Master Chat proves:

- exact write-sets are disjoint;
- no shared router/AppShell conflict;
- no migration overlap;
- current shared integration gates are already merged.

Do not run Stage 9 product implementation concurrently with a serialized Foundation that owns the same shared entry/router files.

## 23. STOP conditions

Return to Master Chat if implementation requires:

- new migration/model;
- device enrollment persistence;
- physical door/turnstile command;
- parent self-service check-in;
- QR/NFC credential;
- pickup-person identity;
- passport data;
- biometrics/face recognition;
- offline attendance queue;
- auth/session redesign;
- shared reserved-file edit outside exact Issue;
- weakening TEACHER assignment checks;
- new PII field;
- production hardware/vendor decision.

## 24. Ordinary defect rule

Fix in the same implementation branch:

- kiosk responsive issue;
- loading/error state;
- state-label bug;
- duplicate-click bug consistent with frozen idempotency;
- API serialization;
- local authorization defect consistent with frozen rules;
- missing targeted test;
- CI failure caused by current work.

Independent architecture/privacy/schema findings return to Master Chat.

## 25. Validation before PR

Backend:

- `ruff check .`;
- Stage 9 targeted pytest;
- relevant Attendance/Stage 6 regression.

Frontend:

- `npm run lint`;
- `npm run build`;
- Stage 9 Playwright spec.

Also:

- `git diff --check`;
- exact write-set inspection;
- synthetic data inspection;
- full required CI.

## 26. S9-ACCEPTANCE

After implementation merge + green post-merge CI, run serialized technical acceptance.

Verify:

- canonical Attendance only;
- all authorized roles;
- assignment/tenant negatives;
- server-local time;
- state idempotency/concurrency;
- online-only fail-closed;
- inactivity logout;
- no browser persistence;
- privacy-minimized roster;
- full relevant regression.

## 27. Future separate gates

Do not absorb into Stage 9 core:

- physical lock/turnstile integration;
- device enrollment/MDM integration;
- parent self-service;
- QR/NFC;
- pickup authorization;
- visitor passes;
- multi-entry event ledger;
- biometrics;
- external camera analytics.

Each requires its own explicit design.

## 28. Desired result

Stage 9 core should make the entrance tablet operationally useful without turning it into a high-risk identity/security subsystem:

```text
one authenticated employee
+ one authorized Group
+ one minimal roster
+ one canonical Attendance record
+ server-controlled timestamps
+ no local PII persistence
```

That is the safest first entrance-kiosk product boundary.