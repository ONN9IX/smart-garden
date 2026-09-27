# Current State

Operational snapshot after Stage 3 acceptance.

- **Baseline main:** `7a4fb52957fb765e1aca532a0a1aa4245096578f` (merge of acceptance PR #91).
- **Stage status:** Stage 1 — FROZEN; Stage 2 — FROZEN; Stage 3 — FROZEN.
- **Current implementation Issue:** none.
- **Next checkpoint:** Stage 4 Design in Chat; design and implementation have not started.

## Technical baseline

- Frontend: Next.js / React / TypeScript.
- Backend: FastAPI / Python / SQLAlchemy / Alembic.
- Database: PostgreSQL only.
- Migrations: `0001` through `0009`; latest is `0009` (`Organization.timezone`).
- API: `/api/v1`, JSON `snake_case`, UUID identifiers.
- Roles: `DIRECTOR`, `ADMIN`, `PARENT`; `TEACHER` remains future scope.
- Auth: server-side sessions, HttpOnly cookie, Argon2id, mandatory temporary-password change and server-side session revocation.
- Tenant: derived only from authenticated User; object access is tenant-scoped and foreign UUIDs follow the active API contract.
- Calendar date: `Organization.timezone` is a validated IANA timezone; synthetic/default organizations use `Europe/Moscow`.

## Delivery checks

- Fast local validation is composed from existing commands: targeted backend `pytest`, `ruff check .`, frontend `npm run lint`, build when relevant, and a targeted Playwright spec when the changed flow requires it.
- Full validation is the existing required CI: complete backend tests on PostgreSQL, Alembic round-trip, frontend lint/build, real browser regression, Docker preview and required gates.
- No parallel fast/full workflow or duplicate scripts are needed.

## Findings

- **Open blockers:** none.
- **Known technical debt:** Issue #32, maintenance of the supported ESLint/GitHub Actions toolchain before production/pilot hardening; it does not block Stage 4 Design.
- Production/pilot still requires a separate current legal, privacy and infrastructure review, including 152-FZ requirements.
