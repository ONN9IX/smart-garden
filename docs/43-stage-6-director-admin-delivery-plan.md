# Stage 6 — DIRECTOR / ADMIN Delivery Plan

**Status:** design proposal for Issue #123; frozen only after PR merge.  
**Owner:** ONN9IX.  
**Track:** Stage 6 Track A — DIRECTOR / ADMIN.

## 1. Goal

Deliver the complete DIRECTOR/ADMIN operational cabinet while F1zname independently delivers the TEACHER cabinet.

Use the largest safe self-contained implementation unit to minimize coordination and Work usage.

Preferred flow:

```text
Track A Design 40–43
→ merge/freeze
→ Stage 6 Design #122 merged
→ S6-FOUNDATION
→ merge + post-merge CI green
→ pre-implementation shared integration preflight
→ S6-MANAGEMENT-CABINET
→ full review
→ merge + post-merge CI
→ integrated Stage 6 acceptance
```

Track A application implementation does not start before Foundation is merged and green.

## 2. Design gate

Issue #123 owns only:

- docs/40-stage-6-director-admin-product-spec.md
- docs/41-stage-6-director-admin-permissions-and-api.md
- docs/42-stage-6-director-admin-data-privacy.md
- docs/43-stage-6-director-admin-delivery-plan.md

No code, migration, tests, CI, dependencies or shared coordination files.

This design may run in parallel with Issue #121 / PR #122 because the write-sets are disjoint.

Before Issue #123 may merge, it must be reconciled against the final merged docs/36–39 and refreshed main if #122 merged after the branch began.

## 3. Foundation dependency

S6-FOUNDATION is owned by F1zname and is serialized.

Track A depends on Foundation for shared:

- TEACHER role/auth support;
- Employee lifecycle compatibility;
- complete Stage 6 teacher-domain schema;
- one migration;
- TeacherGroupAssignment;
- permission primitives;
- shared frontend role/auth/navigation split;
- common router boundary;
- synthetic seed/tests.

Foundation must merge and post-merge CI must be green before Track A code begins.

## 4. Primary implementation Issue

After Foundation, Master Chat creates:

`S6-MANAGEMENT-CABINET`

Owner: ONN9IX.

Preferred delivery:

- one major Issue;
- one branch;
- one PR;
- many internal commits/milestones.

Do not create a Master Chat gate after each screen.

## 5. Internal implementation milestones

Recommended internal order:

1. Management shell/navigation
2. Dashboard/Today
3. Groups
4. Children
5. Guardians
6. Employees
7. Teachers projection/account/assignment UI
8. Attendance
9. Schedule
10. Announcements
11. Teacher Tasks
12. Incidents
13. Polls
14. Group communication management
15. Diary read
16. Notifications
17. Document Notices
18. Photo-consent management
19. Audit UI
20. Settings
21. responsive/mobile pass
22. negative/security tests
23. browser E2E
24. Stage 1–5 + Foundation regression
25. full required CI

These are milestones, not separate Issues unless a STOP condition requires serialization.

## 6. Existing capability reuse

Track A must reuse existing Stage 1–5 APIs for:

- Groups;
- Children;
- Guardians;
- Employees;
- Attendance;
- Announcements;
- Dashboard summary;
- Audit.

Do not create duplicate management API families.

## 7. Track A ownership after Foundation

Exact paths must be determined from the post-Foundation repository, but Track A should prefer isolated management-specific namespaces.

Possible Backend namespaces:

- app/api/management/**
- app/schemas/management/**
- app/services/management/**
- management-specific teacher-management modules where Foundation establishes them

Possible Frontend namespaces:

- app management routes
- features/management/**
- features/director/**
- features/admin/**
- lib/api/management/**
- types/management/**

Do not create a second convention if Foundation establishes a different approved layout.

Repository state after Foundation is authoritative.

## 8. Track B ownership

F1zname owns the complete TEACHER cabinet.

Track A must not implement or redesign:

- /teacher/* functionality;
- teacher Today UI;
- teacher assigned-group UI;
- teacher Attendance UI;
- direct TEACHER↔PARENT communication;
- teacher Diary editing;
- teacher Task-status UI;
- teacher photo content UI.

PARENT-facing communication/diary/poll/photo additions remain Track B where its exact Issue owns them.

## 9. Shared/reserved areas

After Foundation, shared/high-conflict areas include at least the set frozen in docs/39, including:

- shared User/Employee/Group models and model registry;
- auth services;
- shared permissions;
- backend application/router entrypoint;
- Alembic migration head/files;
- shared frontend auth types/AuthGate/AppShell/API client;
- CI workflow;
- AGENTS.md;
- docs/CURRENT_STATE.md;
- README.md.

If Track A needs a reserved area outside its exact Issue:

STOP -> Master Chat -> serialize/rebaseline.

## 10. Pre-implementation shared integration preflight

Before creating S6-MANAGEMENT-CABINET, Master Chat inspects post-Foundation main and verifies:

1. Management routers can be registered without conflicting edits to reserved shared router/entrypoint files.
2. Audit infrastructure supports all frozen Track A actions without conflicting edits to reserved Audit writer infrastructure.
3. No new migration is required.
4. Track A and Track B write-sets are disjoint.
5. Shared frontend navigation exposes an owned management extension point without touching reserved AppShell/auth files.

### If preflight is clean

Create S6-MANAGEMENT-CABINET directly.

### If a minimal shared integration change is necessary

Create one serialized:

`S6-MANAGEMENT-INTEGRATION`

Scope strictly limited to:

- router registration extension point and/or
- Audit allowlist/integration extension point and/or
- equivalent minimal shared hook proven necessary.

No product expansion.

Flow:

```text
S6-MANAGEMENT-INTEGRATION
→ merge
→ post-merge CI green
→ fresh main baseline
→ S6-MANAGEMENT-CABINET
```

## 11. Migration lane

Foundation owns the Stage 6 schema migration.

Expected Track A implementation:

**NO migration.**

Neither Track A nor Track B creates an independent Alembic head during parallel work.

If a later requirement needs schema change:

STOP -> Master Chat -> serialize one migration lane -> merge -> green CI -> fresh baseline.

## 12. Parallel-safe rule

S6-MANAGEMENT-CABINET may run in parallel with S6-TEACHER-CABINET only when:

1. Foundation is merged;
2. post-Foundation CI is green;
3. both active Issues have exact baselines;
4. both are explicitly PARALLEL-SAFE;
5. exact write-sets are disjoint;
6. no reserved shared file is edited;
7. no migration overlap exists;
8. no architecture/API/auth/RBAC/tenant/privacy conflict exists.

Any conflict triggers STOP -> Master Chat.

## 13. Cross-track contracts

### Attendance

One Attendance model.

Track A: all-management operations through existing API.  
Track B: assigned-group teacher operations.

### Announcements

One Announcement model.

Track A: existing management all/group announcement API.  
Track B: teacher own assigned-Group announcements.

### Tasks

One TeacherTask model.

Track A: create/manage/assign.  
Track B: own read/status.

### Incidents

One Incident model.

Track A: same-tenant operational management.  
Track B: assigned Group.

### Communication

Track A: canonical Group thread management.  
Track B: Group and direct TEACHER↔PARENT participant flows.

Track A never gains blanket direct-thread access.

### Photos

Track A: consent state and minimal administrative metadata.  
Track B: consent-gated teacher/parent content flows.

Production storage remains fail-closed.

## 14. Ordinary defect rule

Fix ordinary defects in the same S6-MANAGEMENT-CABINET branch/PR:

- form validation;
- filter bugs;
- responsive UI;
- API serialization;
- local authorization bug consistent with frozen contract;
- missing targeted test;
- CI failure caused by current implementation.

Do not create a corrective Issue for ordinary defects.

## 15. STOP conditions

Return to Master Chat if implementation would require:

- changing frozen Stage 6 architecture/API;
- changing auth/session semantics;
- changing tenant derivation;
- changing permission matrix/RBAC;
- changing Stage 1–5 semantics beyond explicitly additive Stage 6 behavior;
- new migration after Foundation;
- reserved shared-file edit outside exact Issue;
- overlap with F1zname write-set;
- new PII field;
- medical data;
- biometrics/face recognition;
- external production storage;
- external analytics/AI with PII;
- binary document storage;
- retention/legal/hosting decision;
- weakening Stage 5 security or required CI.

## 16. Testing strategy

During implementation run targeted tests for the current module, not necessarily the full suite after every commit.

Before PR handoff run all required validation.

Backend:

- ruff;
- targeted pytest during work;
- full required Backend CI;
- PostgreSQL/migration checks where relevant.

Frontend:

- lint;
- build;
- targeted browser specs;
- final required browser suite.

## 17. Required DIRECTOR E2E

Minimum integrated DIRECTOR flow:

```text
login
→ Dashboard
→ Group
→ Child
→ Guardian
→ Employee
→ ADMIN account lifecycle where applicable
→ TEACHER account/assignment
→ Attendance
→ Schedule
→ Announcement
→ Task
→ Incident
→ Poll
→ Group communication
→ Diary read
→ Notification
→ Document Notice
→ Photo consent
→ Audit
→ Settings
→ logout
```

## 18. Required ADMIN E2E

Minimum ADMIN flow:

```text
login
→ Dashboard
→ Groups/Children/Guardians/Employees
→ Attendance
→ Schedule
→ Announcements
→ Tasks
→ Incidents
→ Polls
→ Group communication
→ Diary read
→ Notifications
→ Document Notices
→ Photo consent
→ logout
```

Also verify forbidden actions:

- Audit;
- Settings write;
- ADMIN account management;
- TEACHER account management;
- TEACHER assignment writes.

## 19. Backend negative tests

At minimum cover:

- cross-tenant major domains;
- wrong-role major routes;
- forged server-owned fields;
- assignment isolation;
- direct-message privacy;
- Notification recipient scope;
- privacy-safe Audit;
- no migration/schema divergence.

## 20. Regression

Keep green:

- Stage 1 Auth;
- Stage 2 Groups/Children/Guardians/PARENT;
- Stage 3 Employees/ADMIN account/Attendance;
- Stage 4 Audit/Announcements/Dashboard;
- Stage 5 security/production/backup-recovery gates;
- Stage 6 Foundation;
- TEACHER frozen boundaries.

Track A may not weaken old tests to make the PR pass.

## 21. Full implementation PR

Preferred title:

`S6-MANAGEMENT-CABINET — DIRECTOR / ADMIN operational cabinet`

PR body must include:

- Issue;
- Owner;
- exact baseline;
- branch/HEAD;
- exact changed files;
- write-set compliance;
- module summary;
- security/tenant summary;
- privacy/Audit summary;
- tests;
- CI;
- findings.

Developer does not self-merge.

## 22. Handoff

Return once the complete Management Cabinet is ready, unless a STOP condition occurs.

Handoff must include:

- Issue / Owner / Baseline / Branch / HEAD / PR;
- changed files and write-set;
- DIRECTOR modules;
- ADMIN modules;
- RBAC/tenant/security;
- privacy/Audit/browser storage;
- targeted/backend/frontend/negative/E2E/regression tests;
- CI;
- BLOCKER / CURRENT STAGE / TECH DEBT / FUTURE.

## 23. Review and finding classification

Master Chat reviews:

Issue -> exact diff -> write-set -> relevant files/tests -> permissions -> tenant -> privacy -> E2E -> CI.

Classify findings:

- BLOCKER
- CURRENT STAGE
- TECH DEBT
- FUTURE

Only BLOCKER/CURRENT STAGE block merge.

Ordinary review defects stay in the same branch.

## 24. Merge/rebaseline

Before merging either parallel Track:

- recheck exact main;
- recheck diff overlap;
- recheck shared/reserved files;
- require green CI.

If one Track merges first, the other rebaselines/reconciles as required and reruns relevant CI before merge.

## 25. Acceptance

Track A delivery is complete only after:

- PR merge;
- post-merge CI green.

Final Stage 6 integrated acceptance occurs after required Track A and complete TEACHER delivery are merged.

It verifies all four roles together and does not imply legal 152-FZ compliance or authorization for a real pilot.

## 26. Future domains

Explicitly separate future design gates:

- Contracts/full document management;
- Billing/payments/fiscalization/debt;
- Financial accounting/analytics;
- Entrance/access-control;
- AI;
- medical module;
- production photo/file infrastructure.

Do not silently absorb them into S6-MANAGEMENT-CABINET.
