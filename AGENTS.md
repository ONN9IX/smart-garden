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
- One Issue → one fresh branch → one implementation → one PR → targeted tests → required CI → Master Chat review → explicit owner authorization for merge.
- Never develop directly in `main`.
- Fix ordinary defects found before merge in the same delivery branch.
- Create a separate corrective Issue only for an independent architecture, API, DB, auth, RBAC, tenant, security, privacy or cross-stage finding.
- Do not run `@codex review` automatically, repeatedly, or after every small fix. It is optional and requires a separate Master Chat decision.
- A developer does not merge a Stage delivery PR without Master Chat acceptance and separate explicit owner authorization. Deploy also requires separate explicit owner authorization.

## Delivery roles and PR acceptance

- Master Chat owns architecture, Issue and WRITE-SET definition, privacy/security analysis, diff and CI review, and the `ACCEPT` or `FIX REQUIRED` decision.
- Codex implements the approved scope and runs targeted local tests.
- GitHub Actions runs all required deterministic test, quality, and security checks. The required PR gate is **8/8 successful checks** on the exact final HEAD.
- The owner separately authorizes merge and deploy; neither is automatic.
- Master Chat reviews scope, behavior, security, tenant isolation, RBAC, privacy, negative scenarios, test coverage, CI, and conflicts. Ordinary fixes stay on the delivery branch.
- Green CI and technical review do not by themselves prove complete security, privacy, or legal compliance.

### Optional AI review

- Automated `@codex review` is not a required gate for every PR and must not be started by default.
- Master Chat may request one final AI review for high-risk auth, RBAC, tenant isolation, personal-data, migration, or architecture changes, or for a serious unresolved defect.
- Do not run AI review cyclically or after each minor correction. If it is unavailable because of limits, Master Chat records the residual risk; merge still requires a separate owner decision.

## Frozen stages and current product baseline

- Master Chat is the single coordination authority.
- **Stages 1–6 are FROZEN** after Stage 6 integrated acceptance Issue #152.
- Frozen active Stage 6 product-code baseline: `31804ef86449ee14de3cab0fe4aedbbf3e9aeacc`.
- Stage 6 includes complete DIRECTOR/ADMIN/TEACHER/PARENT foundations and the current product-module gate.
- Current migration head is `0012_stage6_teacher_foundation.py`.

The line above is the frozen Stage 6 snapshot. The live repository migration head after
approved post-freeze deliveries is `0016_account_access_tokens.py`; new work must verify
the actual Alembic graph rather than treating the historical snapshot as the live head.

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

Read only the current Issue, the relevant part of `docs/CURRENT_STATE.md`, this file, changed or dependent files, and relevant tests. Do not rescan the repository or frozen stages without a concrete regression, compatibility, or security reason.

When available, use Serena for symbols, `rg` for text, `ast-grep`/`sg` for structural search, RTK for large output without hiding diagnostics, and `ccusage` after large tasks. Do not reinstall tools unnecessarily or assume local utilities are available in Codex Cloud.

## Testing

- During implementation, run only targeted tests relevant to the diff.
- Before PR, use existing fast commands as applicable: `ruff check .` and targeted `pytest` from `backend/`; `npm run lint`, build when relevant, and targeted Playwright specs from `frontend/`.
- Full backend/PostgreSQL/migration, frontend, browser, dependency-security and Docker regression belongs to the required 8/8 PR CI and acceptance/freeze checks.
- Do not weaken old tests merely to make a new product change pass. When a capability is OFF, preserve its underlying regression behind explicit test-only feature enabling and add tests for the default OFF boundary.
- Do not bypass branch protection, create auto-agents, call paid APIs, auto-merge, or auto-deploy.
