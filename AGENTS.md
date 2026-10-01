# Repository operating rules

## Stack and architecture

- Frontend: Next.js, React, TypeScript.
- Backend: FastAPI, Python, SQLAlchemy, Alembic.
- Database: PostgreSQL only.
- API: `/api/v1`, JSON `snake_case`, UUID identifiers.
- Do not introduce another backend, database, API or auth stack without an explicit Chat decision.

## Auth, tenant and RBAC

- Authentication uses server-side sessions, an HttpOnly cookie and Argon2id password hashes.
- Implemented roles are `DIRECTOR`, `ADMIN`, `TEACHER`, `PARENT`.
- Derive tenant only from the authenticated User. Every object query must be tenant-scoped; handle foreign UUIDs according to the current API contract.
- TEACHER access is assignment-scoped and PARENT access is ChildGuardian/participant-scoped.
- Do not change RBAC architecture without an explicit Master Chat decision.

## Personal data

- Minimize personal data and add no speculative fields.
- Dev, test and preview data must be synthetic only.
- Every new function requires a privacy and 152-FZ review.
- A technical review alone must never be presented as production legal compliance.

## Fast Flow and Git

- Design/freeze product decisions in Chat before implementation.
- One major delivery Issue → one fresh branch → implementation → targeted tests → PR → CI → review → merge.
- Never develop directly in `main`.
- Fix ordinary defects found before merge in the same delivery branch.
- Create a separate corrective Issue only for an independent architecture, API, DB, auth, RBAC, tenant, security, privacy or cross-stage finding.
- A developer does not merge a Stage delivery PR without an explicit Master Chat decision.

## Frozen stages and current product baseline

- Master Chat is the single coordination authority.
- **Stages 1–6 are FROZEN** after Stage 6 integrated acceptance Issue #152.
- Frozen active Stage 6 product-code baseline: `31804ef86449ee14de3cab0fe4aedbbf3e9aeacc`.
- Stage 6 includes complete DIRECTOR/ADMIN/TEACHER/PARENT foundations and the current product-module gate.
- Current migration head is `0012_stage6_teacher_foundation.py`.

### Active product modules

Keep ON unless a new explicit Master Chat decision changes them:

- Dashboard;
- Children;
- Groups;
- Guardians/Parents;
- Employees;
- Teachers/assignments;
- Attendance;
- Schedule;
- Announcements;
- Tasks;
- Communications;
- Notifications;
- Audit;
- Organization Settings;
- Auth/account management.

### Deferred modules

The following implemented capabilities are **OFF but preserved**:

- Polls;
- Incidents;
- Diary;
- Photos;
- Photo consents;
- Document notices.

OFF means hidden from product UI and blocked at the API boundary; code/models/data are not deleted. Re-enable only through an explicit Master Chat Issue with regression tests.

### Paused future runtime

Design docs may exist, but runtime implementation is not authorized until Master Chat explicitly restarts it:

- Stage 7 Contracts/Billing/Payments/Debt/Receipts;
- Stage 9 Entry Kiosk;
- Stage 10 production protected-storage rollout while dependent modules are OFF;
- Stage 11 Development Support / psychology / individual approach;
- Stage 12 SaaS tenant subscription.

Do not infer authorization to implement a future Stage merely because its design documents exist.

## Coordination

- Every implementation Issue has one owner, an exact baseline, an explicit write-set and one branch/PR.
- Parallel work is allowed only when Master Chat marks every participating Issue `PARALLEL-SAFE: YES` and write-sets are disjoint.
- Shared/high-conflict files are serialized by default: CI workflow, dependency/lock files, shared backend entry/config/model files, Alembic migration head, `AGENTS.md`, `docs/CURRENT_STATE.md`, root `README.md` and shared operating docs.
- A frozen-contract, privacy, migration, shared-file or write-set conflict requires STOP → Master Chat → serialize/rebaseline.

## Context economy

Read in this order:

1. current Issue;
2. current Stage/product contract;
3. `docs/CURRENT_STATE.md`;
4. this file;
5. changed files/diff;
6. relevant tests and CI.

Do not rescan frozen stages without a concrete regression, compatibility or security reason.

## Testing

- During implementation, run only targeted tests relevant to the diff.
- Before PR, use existing fast commands as applicable: `ruff check .` and targeted `pytest` from `backend/`; `npm run lint`, build when relevant, and targeted Playwright specs from `frontend/`.
- Full backend/PostgreSQL/migration, frontend, browser, dependency-security and Docker regression belongs to required PR CI and acceptance/freeze checks.
- Do not weaken old tests merely to make a new product change pass. When a capability is OFF, preserve its underlying regression behind explicit test-only feature enabling and add tests for the default OFF boundary.
