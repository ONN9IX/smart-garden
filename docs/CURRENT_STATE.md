# Current State

Operational snapshot after the Stage 4 Audit delivery.

- **Delivery baseline:** `7f240be022a9e79a45d50510e869a1aeeb2c9601` (fresh `main` after Stage 4 Design PR #93).
- **Stage status:** Stage 1 — FROZEN; Stage 2 — FROZEN; Stage 3 — FROZEN; Stage 4 Design — FROZEN; Stage 4 implementation is not yet accepted/frozen.
- **Latest implemented delivery:** Issue #94, immutable business Audit vertical slice.
- **Current implementation Issue:** none after merge of this delivery.
- **Next checkpoint:** Issue #95 delivery; no Stage 4 acceptance has been performed.

## Technical baseline

- Frontend: Next.js / React / TypeScript.
- Backend: FastAPI / Python / SQLAlchemy / Alembic.
- Database: PostgreSQL only.
- Migrations: `0001` through `0010`; latest is `0010` (`audit_events`).
- API: `/api/v1`, JSON `snake_case`, UUID identifiers.
- Roles: `DIRECTOR`, `ADMIN`, `PARENT`; `TEACHER` remains future scope.
- Auth: server-side sessions, HttpOnly cookie, Argon2id, mandatory temporary-password change and server-side session revocation.
- Tenant: derived only from authenticated User; object access is tenant-scoped and foreign UUIDs follow the active API contract.
- Calendar date: `Organization.timezone` is a validated IANA timezone; synthetic/default organizations use `Europe/Moscow`.
- Audit: append-only tenant-scoped business events; DIRECTOR-only read API/UI; details are structurally whitelisted and privacy-minimized.

## Delivery checks

- Fast local validation is composed from existing commands: targeted backend `pytest`, `ruff check .`, frontend `npm run lint`, build when relevant, and a targeted Playwright spec when the changed flow requires it.
- Full validation is the existing required CI: complete backend tests on PostgreSQL, Alembic round-trip, frontend lint/build, real browser regression, Docker preview and required gates.
- No parallel fast/full workflow or duplicate scripts are needed.

## Findings

- **Open blockers:** none.
- **Known technical debt:** Issue #32, maintenance of the supported ESLint/GitHub Actions toolchain before production/pilot hardening; it does not block Stage 4 Design.
- Production/pilot still requires a separate current legal, privacy and infrastructure review, including 152-FZ requirements.
