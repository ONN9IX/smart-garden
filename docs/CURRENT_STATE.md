# Current State

Operational snapshot after the Stage 5 design freeze.

- **Stage 5 design-freeze baseline:** `3ba76177d27c4ae62092e85acfefb456daf510f4` (Issue #103 / PR #105 completed and merged; post-merge CI run #108 succeeded 6/6).
- **Stage 4 frozen baseline:** `69291f1a0c99df80c76e899c146ea9d6c3bd341f` (acceptance PR #101); later documentation and Stage 5 design commits do not change that frozen Stage 4 contract.
- **Stage status:** Stage 1 — FROZEN; Stage 2 — FROZEN; Stage 3 — FROZEN; Stage 4 — FROZEN; Stage 5 Design — FROZEN.
- **Completed Stage 4 deliveries:** Issue #94 / PR #96 (Audit) and Issue #95 / PR #97 (Announcements and Dashboard).
- **Completed corrective:** Issue #99 / PR #100, deterministic Attendance Audit test without production contract changes.
- **Completed Stage 5 design gate:** Issue #103 / PR #105; Issue #102 remains the coordination contract.
- **Next implementation gate:** Wave 1 Issues #106 (ONN9IX — Production & Security) and #107 (F1zname — Backup & Recovery). They remain blocked until Issue #108 is merged and Master Chat refreshes their exact common baseline. Live execution status and exact implementation baselines are tracked in those Issues and Master Chat coordination.

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

These documents were frozen by Issue #103 / PR #105 at `3ba76177d27c4ae62092e85acfefb456daf510f4`. They do not authorize implementation by themselves; future design changes require a new explicit Master Chat decision.
