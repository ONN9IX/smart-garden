# Current State

Operational snapshot after Stage 5 technical acceptance and the Stage 6 design freeze.

- **Stage 5 design-freeze baseline:** `3ba76177d27c4ae62092e85acfefb456daf510f4` (Issue #103 / PR #105 completed and merged; post-merge CI run #108 succeeded 6/6).
- **Stage 5 Wave 1 baseline:** `0b036829fee56b3aedc4185fb20b7dee406d9954` (Issues #106 and #107 / PRs #110 and #111 completed and merged; post-merge CI run #118 succeeded 7/7).
- **Stage 5 implementation baseline:** `762ee9f2fce45372e4b771c788fd054fbb2272ce` (Track D Issue #115 / PR #116 completed and merged; post-merge CI run #123 succeeded 8/8).
- **Stage 5 final frozen baseline:** `b4f0c764b17b6df40464d3d8d344cea3f1ed3e1b` (Issue #117 / PR #118 completed and merged; acceptance PR CI run #124 rerun attempt 2 succeeded 8/8; post-merge CI run #125 succeeded 8/8).
- **Stage 4 frozen baseline:** `69291f1a0c99df80c76e899c146ea9d6c3bd341f` (acceptance PR #101); later documentation and Stage 5 design commits do not change that frozen Stage 4 contract.
- **Stage status:** Stages 1–5 — FROZEN; Stage 5 technical acceptance — ACCEPTED / FROZEN by Issue #117 / PR #118; Stage 6 Design — FROZEN by Issue #121 / its design PR; Stage 6 implementation — NOT STARTED.
- **Completed Stage 4 deliveries:** Issue #94 / PR #96 (Audit) and Issue #95 / PR #97 (Announcements and Dashboard).
- **Completed corrective:** Issue #99 / PR #100, deterministic Attendance Audit test without production contract changes.
- **Completed Stage 5 design gate:** Issue #103 / PR #105; Stage 5 coordination Issue #102 was closed by acceptance PR #118.
- **Completed Stage 5 Wave 1:** Issue #106 / PR #110 (Production & Security) and Issue #107 / PR #111 (Backup & Recovery).
- **Completed Stage 5 Track C:** Issue #112 / PR #113 (CI, toolchain and supply-chain hardening); Issue #32 was absorbed and closed. Track C fresh-main baseline is `bfa2ccd287c3dbe35a968aee24ad6bba64c5d63f`, and post-merge CI run #120 succeeded 8/8.
- **Completed Stage 5 Track D:** Issue #115 / PR #116 (operations, session cleanup and pilot runbooks), merged at the Stage 5 implementation baseline above.
- **Completed Stage 5 acceptance gate:** Issue #117 / PR #118 recorded the acceptance matrix, final regression and freeze; both Issue #117 and coordination Issue #102 closed with the acceptance merge.
- **Stage 6 pre-design baseline:** `471bdad125f3682c5924ad1e52dd642e75942e23` (Issue #121, design-only TEACHER cabinet and parallel-delivery contract).
- **Next gate:** `S6-FOUNDATION`, created explicitly by Master Chat from the post-design-merge exact baseline. Parallel ONN9IX/F1zname implementation is forbidden until Foundation merges and post-merge CI is green.

## Technical baseline

- Frontend: Next.js / React / TypeScript.
- Backend: FastAPI / Python / SQLAlchemy / Alembic.
- Database: PostgreSQL only.
- Migrations: `0001` through `0011`; latest is `0011` (`announcements`).
- API: `/api/v1`, JSON `snake_case`, UUID identifiers.
- Implemented roles remain `DIRECTOR`, `ADMIN`, `PARENT`. Stage 6 design conceptually freezes `DIRECTOR`, `ADMIN`, `TEACHER`, `PARENT`; `TEACHER` is not implemented or available in production until Stage 6 implementation acceptance.
- Auth: server-side sessions, HttpOnly cookie, Argon2id, mandatory temporary-password change and server-side session revocation.
- Tenant: derived only from authenticated User; object access is tenant-scoped and foreign UUIDs follow the active API contract.
- Calendar date: `Organization.timezone` is a validated IANA timezone; synthetic/default organizations use `Europe/Moscow`.
- Audit: append-only tenant-scoped business events; DIRECTOR-only read API/UI; details are structurally whitelisted and privacy-minimized.
- Announcements: immediate active publication for whole garden or active same-tenant Group; archive-only lifecycle; DIRECTOR/ADMIN management.
- Dashboard: garden-local current operational summary for DIRECTOR/ADMIN; active/current-group aggregation and missing/explicit `unknown` semantics.

## Delivery checks

- Fast local validation is composed from existing commands: targeted backend `pytest`, `ruff check .`, frontend `npm run lint`, build when relevant, and a targeted Playwright spec when the changed flow requires it.
- Full validation is the existing required CI: Backend quality, Frontend quality, Dependency security, Browser auth flow, Local browser preview, PostgreSQL backup and recovery, Backend checks and Frontend checks. Dependency security and PostgreSQL recovery remain required components.
- No parallel fast/full workflow or duplicate scripts are needed.

## Findings

- **Open BLOCKER findings:** none.
- **Open CURRENT STAGE findings:** none.
- **Known technical debt:** Issue #32 was absorbed and closed by Issue #112 / PR #113 through Next.js/ESLint compatibility verification and current GitHub Actions majors. ESLint 9 is compatible with the locked Next.js configuration but is EOL; ESLint 10 remains deferred until the complete upstream plugin set supports it without peer overrides or lint failure.
- Real-pilot prerequisites remain unresolved: legal/privacy specialist review; operator/controller/processor roles; hosting, jurisdiction/data location, subprocessors and data flows; business-data retention/destruction; production backup protection/location/retention; access administration/revocation; and deployment-specific login-abuse topology/threshold/window and verification. Technical acceptance does not authorize a real pilot, real PII or claim full legal compliance with 152-FZ.

## Stage 5 design documents

- `docs/27-stage-5-design-and-decisions.md`
- `docs/28-stage-5-security-and-production.md`
- `docs/29-stage-5-operations-and-pilot.md`
- `docs/30-stage-5-delivery-plan.md`
- `docs/31-stage-5-production-security-implementation.md`
- `docs/32-stage-5-backup-and-recovery.md`
- `docs/33-stage-5-ci-toolchain-supply-chain.md`
- `docs/34-stage-5-operations-session-cleanup.md`
- `docs/35-stage-5-acceptance.md`

Documents 27–30 were frozen by Issue #103 / PR #105 at `3ba76177d27c4ae62092e85acfefb456daf510f4`. Documents 31–34 record Stage 5 implementation, and document 35 records final technical acceptance. They do not change the frozen Stage 1–4 product contract; future design changes require a new explicit Master Chat decision.

## Stage 6 design documents

- `docs/36-stage-6-teacher-design-and-decisions.md`
- `docs/37-stage-6-permissions-and-api.md`
- `docs/38-stage-6-data-model-privacy-and-tests.md`
- `docs/39-stage-6-parallel-delivery-plan.md`

Documents 36–39 freeze the Stage 6 TEACHER architecture, permission/API contract, complete Foundation schema, privacy/test requirements and serialized-to-parallel delivery plan. They do not implement TEACHER. Stages 1–5 remain frozen, the next gate is `S6-FOUNDATION`, and real-pilot/privacy boundaries remain in force.
