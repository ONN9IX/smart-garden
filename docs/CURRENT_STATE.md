# Current State

Operational snapshot during Stage 5 implementation.

- **Stage 5 design-freeze baseline:** `3ba76177d27c4ae62092e85acfefb456daf510f4` (Issue #103 / PR #105 completed and merged; post-merge CI run #108 succeeded 6/6).
- **Stage 5 Wave 1 baseline:** `0b036829fee56b3aedc4185fb20b7dee406d9954` (Issues #106 and #107 / PRs #110 and #111 completed and merged; post-merge CI run #118 succeeded 7/7).
- **Stage 4 frozen baseline:** `69291f1a0c99df80c76e899c146ea9d6c3bd341f` (acceptance PR #101); later documentation and Stage 5 design commits do not change that frozen Stage 4 contract.
- **Stage status:** Stage 1 — FROZEN; Stage 2 — FROZEN; Stage 3 — FROZEN; Stage 4 — FROZEN; Stage 5 Design — FROZEN; Stage 5 Implementation — IN PROGRESS.
- **Completed Stage 4 deliveries:** Issue #94 / PR #96 (Audit) and Issue #95 / PR #97 (Announcements and Dashboard).
- **Completed corrective:** Issue #99 / PR #100, deterministic Attendance Audit test without production contract changes.
- **Completed Stage 5 design gate:** Issue #103 / PR #105; Issue #102 remains the coordination contract.
- **Completed Stage 5 Wave 1:** Issue #106 / PR #110 (Production & Security) and Issue #107 / PR #111 (Backup & Recovery).
- **Completed Stage 5 Track C:** Issue #112 / PR #113 (CI, toolchain and supply-chain hardening); Issue #32 was absorbed and closed. Track C fresh-main baseline is `bfa2ccd287c3dbe35a968aee24ad6bba64c5d63f`, and post-merge CI run #120 succeeded 8/8.
- **Current implementation gate:** Track D / Issue #115 (operations, session cleanup and pilot runbooks). Live execution status remains tracked in the Issue and Master Chat coordination.
- **Next sequencing constraint:** Do not start Wave 3 until Track D is merged, reconciled and Master Chat assigns an exact fresh-main baseline.

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
- Full validation is the existing required CI: complete backend tests on PostgreSQL, Alembic round-trip, frontend lint/build, locked Python and Node dependency security audits, real browser regression, Docker preview, PostgreSQL recovery verification and required gates. Dependency security remains a required CI component after Track C.
- No parallel fast/full workflow or duplicate scripts are needed.

## Findings

- **Open BLOCKER findings:** none.
- **Open CURRENT STAGE findings:** none; the acceptance finding was corrected by Issue #99 / PR #100.
- **Known technical debt:** Issue #32 was absorbed and closed by Issue #112 / PR #113 through Next.js/ESLint compatibility verification and current GitHub Actions majors. ESLint 9 is compatible with the locked Next.js configuration but is EOL; ESLint 10 remains deferred until the complete upstream plugin set supports it without peer overrides or lint failure.
- Production/pilot still requires a separate current legal, privacy, retention and infrastructure review, including current 152-FZ requirements; technical acceptance alone is not a legal-compliance claim.

## Stage 5 design documents

- `docs/27-stage-5-design-and-decisions.md`
- `docs/28-stage-5-security-and-production.md`
- `docs/29-stage-5-operations-and-pilot.md`
- `docs/30-stage-5-delivery-plan.md`
- `docs/31-stage-5-production-security-implementation.md`
- `docs/32-stage-5-backup-and-recovery.md`
- `docs/33-stage-5-ci-toolchain-supply-chain.md`
- `docs/34-stage-5-operations-session-cleanup.md`

Documents 27–30 were frozen by Issue #103 / PR #105 at `3ba76177d27c4ae62092e85acfefb456daf510f4`. Documents 31–33 record the corresponding Stage 5 implementation. They do not change the frozen Stage 1–4 product contract; future design changes require a new explicit Master Chat decision.
