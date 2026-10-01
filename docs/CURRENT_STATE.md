# Current State

Operational snapshot at Stage 6 integrated acceptance.

## Frozen baseline

- **Stages 1–5:** FROZEN.
- **Stage 6 Design:** FROZEN.
- **Stage 6 implementation:** complete across DIRECTOR / ADMIN / TEACHER / PARENT.
- **Stage 6 technical acceptance:** ACCEPTED / FROZEN by Issue #152 once its acceptance PR merges with green required CI.
- **Frozen active product-code baseline:** `31804ef86449ee14de3cab0fe4aedbbf3e9aeacc`.
- PR #141 merged the complete TEACHER/PARENT Stage 6 delivery at `649ca371ba202651ca4a167e71d8d5380486bb91`.
- Issue #150 / PR #151 then applied the current reversible product-module OFF baseline without deleting code/models/data.

Acceptance evidence:
- PR #141 final CI **#204 — SUCCESS 8/8**.
- PR #141 post-merge CI **#205 — SUCCESS 8/8**.
- Product-module flags final CI **#210 — SUCCESS 8/8**.

Before Issue #152 started there were no open Issues or PRs.

## Technical baseline

- Frontend: Next.js / React / TypeScript.
- Backend: FastAPI / Python / SQLAlchemy / Alembic.
- Database: PostgreSQL only.
- Migrations: `0001` through `0012`; latest is `0012_stage6_teacher_foundation.py`.
- API: `/api/v1`, JSON `snake_case`, UUID identifiers.
- Implemented roles: `DIRECTOR`, `ADMIN`, `TEACHER`, `PARENT`.
- Auth: server-side sessions, HttpOnly cookie, Argon2id, mandatory temporary-password change and server-side session revocation.
- Tenant: derived only from authenticated User.
- TEACHER: active Employee/assignment scoped.
- PARENT: active Guardian/ChildGuardian and participant scoped.
- Calendar date: `Organization.timezone` is validated IANA timezone.
- Audit: append-only tenant-scoped business events, DIRECTOR-only read, privacy-minimized details.

## Active product modules

### Management

- Dashboard / Today
- Children
- Groups
- Guardians / Parents
- Employees
- Teachers
- Teacher assignments
- Attendance
- Schedule
- Announcements
- Tasks
- Group communications
- Notifications
- Audit — DIRECTOR only
- Organization Settings — DIRECTOR only
- account management according to RBAC

### TEACHER

- Today
- assigned Groups/roster
- eligible Guardian context
- Attendance
- Schedule
- Announcements
- Group/direct communications
- own Tasks
- own Notifications

### PARENT

- linked Children context
- eligible Announcements
- Group/direct communications

## OFF but preserved

These implemented capabilities are hidden from active UI and blocked at API entry by the central product feature gate:

- Polls
- Incidents
- Diary
- Photos
- Photo consents
- Document notices

Their code/models/data are retained. Existing capability regression can explicitly enable them inside tests. Re-enable only by explicit Master Chat decision.

## Paused future runtime

Design documentation is retained, but runtime work is STOPPED until explicitly restarted:

- Stage 7 — Contracts/Billing/Payments/Debt/Receipts
- Stage 9 — Entry Kiosk / entrance tablet
- Stage 10 — production Protected Storage rollout while dependent modules remain OFF
- Stage 11 — Development Support / psychology / individual approach
- Stage 12 — SaaS tenant subscription

The entrance workflow currently remains staff-operated Attendance; there is no kiosk runtime.

## Delivery checks

Required CI remains:

- Backend quality
- Frontend quality
- Dependency security
- Browser auth flow
- Local browser preview
- PostgreSQL backup and recovery
- Backend checks
- Frontend checks

Stage 6 acceptance requires all of them green.

## Findings

- **Open BLOCKER findings:** none.
- **Open CURRENT STAGE findings:** none.
- **Known technical debt:** ESLint 9 compatibility/EOL debt remains; ESLint 10 stays deferred until upstream compatibility is safe.
- **Real-pilot prerequisites remain unresolved:** legal/privacy specialist review; operator/controller/processor roles; hosting/data location/subprocessors; business retention/destruction; production backup protection/location/retention; access administration/revocation; deployment-specific login-abuse controls. Technical acceptance does not authorize a real-PII pilot or claim full 152-FZ compliance.

## Stage 6 documents

Core Stage 6 design:
- `docs/36-stage-6-teacher-design-and-decisions.md`
- `docs/37-stage-6-permissions-and-api.md`
- `docs/38-stage-6-data-model-privacy-and-tests.md`
- `docs/39-stage-6-parallel-delivery-plan.md`
- `docs/40-stage-6-director-admin-product-spec.md`
- `docs/41-stage-6-director-admin-permissions-and-api.md`
- `docs/42-stage-6-director-admin-data-privacy.md`
- `docs/43-stage-6-director-admin-delivery-plan.md`

Final integrated acceptance:
- `docs/68-stage-6-integrated-acceptance.md`

The product-module OFF decision in Issue #150 / PR #151 is a later explicit Master Chat scope override for active exposure. It does not delete the frozen underlying Stage 6 capability code.

## Next gate

No new runtime Stage starts automatically.

The next implementation/re-enable gate must be created explicitly by Master Chat from the fresh post-acceptance `main` baseline with a precise scope, owner, write-set, privacy review and CI plan.
