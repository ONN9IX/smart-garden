# Current State

Operational snapshot during the Stage 5 design gate.

- **Current design baseline:** `ea8de68545b96a5f7339cf5ab32e3f471e86d606`.
- **Stage 4 frozen baseline:** `69291f1a0c99df80c76e899c146ea9d6c3bd341f` (acceptance PR #101); the current design baseline additionally includes the post-Stage-4 docs cleanup.
- **Stage status:** Stage 1 — FROZEN; Stage 2 — FROZEN; Stage 3 — FROZEN; Stage 4 — FROZEN; Stage 5 Design Gate — IN PROGRESS; Stage 5 implementation — NOT STARTED.
- **Completed Stage 4 deliveries:** Issue #94 / PR #96 (Audit) and Issue #95 / PR #97 (Announcements and Dashboard).
- **Completed corrective:** Issue #99 / PR #100, deterministic Attendance Audit test without production contract changes.
- **Current Issue:** #103 — Stage 5 design-freeze gate. Issue #102 is its coordination contract.
- **Next checkpoint:** review and merge the Issue #103 docs-only PR. No Stage 5 implementation Issue may start before that design is merged and frozen by Master Chat.

## Technical baseline

- Frontend: Next.js / React / TypeScript.
- Backend: FastAPI / Python / SQLAlchemy / Alembic.
- Database: PostgreSQL only.
- Migrations: `0001` through `0011`; latest is `0011` (`announcements`).
- API: `/api/v1`, JSON `snake_case`, UUID identifiers.
- Roles: `DIRECTOR`, `ADMIN`, `PARENT`; `TEACHER` remains future scope.
- Auth: server-side sessions, HttpOnly cookie, Argon2id, mandatory temporary-password change and server-side session revocation.
- Tenant: derived only from authenticated User; object access is tenant-scoped and foreign UUIDs follow the active API contract.
- Calendar date: `Organization.timezone` is a validated IANA timezone; synthetic/default organizations use `Europe/Moscow`.
- Audit: append-only tenant-scoped business events; DIRECTOR-only read API/UI; details are structurally whitelisted and privacy-minimized.
- Announcements: immediate active publication for whole garden or active same-tenant Group; archive-only lifecycle; DIRECTOR/ADMIN management.
- Dashboard: garden-local current operational summary for DIRECTOR/ADMIN; active/current-group aggregation and missing/explicit `unknown` semantics.

## Delivery checks

- Fast local validation is composed from existing commands: targeted backend `pytest`, `ruff check .`, frontend `npm run lint`, build when relevant, and a targeted Playwright spec when the changed flow requires it.
- Full validation is the existing required CI: complete backend tests on PostgreSQL, Alembic round-trip, frontend lint/build, real browser regression, Docker preview and required gates.
- No parallel fast/full workflow or duplicate scripts are needed.

## Findings

- **Open BLOCKER findings:** none.
- **Open CURRENT STAGE findings:** none; the acceptance finding was corrected by Issue #99 / PR #100.
- **Known technical debt:** Issue #32, maintenance of the supported ESLint/GitHub Actions toolchain before production/pilot hardening; it does not block Stage 4 freeze.
- Production/pilot still requires a separate current legal, privacy, retention and infrastructure review, including current 152-FZ requirements; technical acceptance alone is not a legal-compliance claim.

## Stage 5 design documents

- `docs/27-stage-5-design-and-decisions.md`
- `docs/28-stage-5-security-and-production.md`
- `docs/29-stage-5-operations-and-pilot.md`
- `docs/30-stage-5-delivery-plan.md`

These documents are IN PROGRESS until Issue #103 is reviewed and merged. They do not authorize implementation by themselves.
