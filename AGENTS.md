# Repository operating rules

## Stack and architecture

- Frontend: Next.js, React, TypeScript.
- Backend: FastAPI, Python, SQLAlchemy, Alembic.
- Database: PostgreSQL only.
- API: `/api/v1`, JSON `snake_case`, UUID identifiers.
- Do not introduce another backend, database, API or auth stack without an explicit Chat decision.

## Auth, tenant and RBAC

- Authentication uses server-side sessions, an HttpOnly cookie and Argon2id password hashes.
- Derive tenant only from the authenticated User. Every object query must be tenant-scoped; handle foreign UUIDs according to the current API contract.
- Do not change the RBAC architecture without an explicit Chat decision.

## Personal data

- Minimize personal data and add no speculative fields.
- Dev, test and preview data must be synthetic only.
- Every new function requires a privacy and 152-FZ review.
- A technical review alone must never be presented as production legal compliance.

## Fast Flow and Git

- Design the Stage in Chat and freeze its decisions before Work begins.
- One major delivery Issue → one fresh branch → implementation → targeted tests → PR → CI → review → merge. Never develop directly in `main`.
- Fix ordinary defects found before merge in the same delivery branch.
- Create a separate corrective Issue only for an independent architecture, API, DB, auth, RBAC, tenant, security, privacy or cross-stage finding.

## Context economy

Read in this order: current Issue, current Stage contract, `docs/CURRENT_STATE.md`, this file, changed files/diff, relevant tests and CI. Do not scan frozen stages without a demonstrated reason.

## Testing

- During implementation, run only targeted tests relevant to the diff.
- Before PR, use existing fast commands as applicable: `ruff check .` and targeted `pytest` from `backend/`; `npm run lint`, `npm run build` when types/build are affected, and `npm run test:e2e -- <spec>` from `frontend/` for relevant browser paths.
- Full backend/PostgreSQL/migration, frontend, browser and Docker regression belongs to required PR CI and acceptance/freeze checks.
- Do not repeat an unchanged full suite without a reason and do not weaken required CI gates.
