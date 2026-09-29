# Stage 5 — Delivery Plan

Status: **DESIGN GATE IN PROGRESS**. No implementation Track may begin until Issue #103 is reviewed, merged and frozen and Master Chat creates its exact-baseline delivery Issue.

## Issue contract

Every Stage 5 implementation Issue must contain:

- Goal and Owner (`ONN9IX` or `F1zname`);
- exact fresh-main baseline SHA and branch name;
- Scope and explicit Out of scope;
- exact Write-set and forbidden/shared files;
- Dependencies and merge order;
- `PARALLEL-SAFE: YES/NO`;
- validation and Definition of Done;
- required handoff format.

One Issue → one branch → one PR. A developer does not merge a Stage 5 PR without an explicit Master Chat decision. Work outside the write-set or a newly discovered BLOCKER/CURRENT STAGE finding requires STOP and handoff to Master Chat.

## Wave 1 — parallel after design freeze

### Track A — ONN9IX: Production and Security

Expected future Issue scope:

- production configuration validation;
- cookie, Origin and shared-environment hardening;
- targeted security tests;
- pilot login-abuse control only if repository/application implementation is actually required by the selected deployment topology.

### Track B — F1zname: Backup and Recovery

Expected future Issue scope:

- PostgreSQL-native backup/restore scripts;
- disposable synthetic restore verification;
- recovery runbook and guarded destructive steps;
- no production business-contract changes.

Tracks A and B may start in parallel only when Master Chat creates two separate Issues from the same exact fresh-main baseline, gives them non-overlapping write-sets and marks both `PARALLEL-SAFE: YES`.

## Wave 2 — after Wave 1 reconciliation

Wave 2 starts from the reconciled main baseline after Wave 1 merge/rebase and required CI.

### Track C — ONN9IX: CI, Toolchain and Supply Chain

Expected future Issue scope includes the intent of Issue #32:

- supported GitHub Actions majors;
- ESLint/Next.js toolchain compatibility;
- repository-appropriate dependency/security checks;
- preservation of all existing required gates, including PostgreSQL, browser and Docker preview evidence;
- no unapproved upload of repository or business data to third-party scanners.

### Track D — F1zname: Operations, Session Cleanup and Pilot Runbooks

Expected future Issue scope:

- internal operational cleanup for expired/revoked sessions;
- availability/monitoring procedure;
- incident and failure-response checklists;
- pilot operational runbooks.

If Track D needs a shared/high-conflict application or configuration file, it must STOP and return to Master Chat. Tracks C and D are parallel only with explicit non-overlapping Issues marked `PARALLEL-SAFE: YES`.

## Wave 3 — serialized integration and acceptance

After Waves 1 and 2 are merged and reconciled:

1. reconcile onboarding and operational documentation;
2. run complete pilot-readiness regression through required CI;
3. complete the technical privacy/legal/infrastructure checklist while keeping unresolved legal decisions explicit;
4. perform Stage 5 acceptance with no BLOCKER/CURRENT STAGE findings;
5. update `docs/CURRENT_STATE.md` and record the final Stage 5 freeze through Master Chat.

## Shared/high-conflict files

The following are serialized by default and must not be assigned concurrently to two developers:

- `.github/workflows/ci.yml`;
- `backend/requirements.in` and `backend/requirements.txt`;
- `frontend/package.json` and `frontend/package-lock.json`;
- `backend/app/main.py` and `backend/app/core/config.py`;
- `backend/app/models/__init__.py`;
- Alembic migration head or any new migration;
- `AGENTS.md`, `docs/CURRENT_STATE.md`, root `README.md` and shared operating docs.

An exception requires an explicit Master Chat decision and stated merge order.

## Handoff

Every Track returns Issue, owner, baseline, branch, HEAD, PR, changed files, write-set compliance, validation/tests, CI, findings and dependency/merge notes. Master Chat performs Issue → diff → validation → CI review and alone decides merge order.
