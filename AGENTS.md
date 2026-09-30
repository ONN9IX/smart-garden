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

## Frozen stages and coordination

- Master Chat is the single coordination authority. Stages 1–5 are FROZEN.
- Stage 6 Design is FROZEN by Issue #121 and its design PR. Stage 6 implementation is NOT STARTED; the next gate is the serialized `S6-FOUNDATION` Issue created explicitly by Master Chat.
- The Stage 6 order is design merge/freeze → Foundation → Foundation merge → post-merge CI green → parallel implementation. No ONN9IX/F1zname implementation starts before that gate is complete.
- After Foundation and green post-merge CI, ONN9IX owns only explicitly disjoint DIRECTOR/ADMIN Track A Issues and F1zname receives one major autonomous `S6-TEACHER-CABINET` Issue, branch and PR for the complete cabinet. Internal TEACHER modules are not separate Master Chat gates; ordinary defects stay in that branch. Shared auth/models/migrations/AppShell/CI/`AGENTS.md`/`docs/CURRENT_STATE.md`/root `README.md` remain reserved; a frozen-contract, privacy, migration, shared-file or write-set conflict requires STOP → Master Chat → serialize/rebaseline.
- Every Issue has one owner, an exact baseline, an explicit write-set and one branch/PR. Work outside the write-set requires STOP and handoff to Master Chat.
- Parallel work is allowed only when Master Chat marks every participating Issue `PARALLEL-SAFE: YES` and their write-sets do not overlap.
- Shared/high-conflict files are serialized by default: CI workflow, dependency/lock files, shared backend entry/config/model files, Alembic migration head, `AGENTS.md`, `docs/CURRENT_STATE.md`, root `README.md` and shared operating docs.
- A developer does not merge a Stage delivery PR without an explicit Master Chat decision.

## Context economy

Read in this order: current Issue, current Stage contract, `docs/CURRENT_STATE.md`, this file, changed files/diff, relevant tests and CI. Do not scan frozen stages without a concrete regression, compatibility or security reason.

## Testing

- During implementation, run only targeted tests relevant to the diff.
- Before PR, use existing fast commands as applicable: `ruff check .` and targeted `pytest` from `backend/`; `npm run lint`, `npm run build` when types/build are affected, and `npm run test:e2e -- <spec>` from `frontend/` for relevant browser paths.
- Full backend/PostgreSQL/migration, frontend, browser and Docker regression belongs to required PR CI and acceptance/freeze checks.
- Do not repeat an unchanged full suite without a reason and do not weaken required CI gates.
