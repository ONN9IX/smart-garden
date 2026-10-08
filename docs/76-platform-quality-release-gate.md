# Platform quality, compatibility and release gate

This contract is QA infrastructure for ПРОМАКС. It does not add product features,
change RBAC/tenant rules, enable OFF/STOP domains, or establish legal compliance with
152-ФЗ. All automated data is synthetic.

## Supported production lane

The required PR workflow remains pinned to Python 3.12, Node 22, PostgreSQL 16,
Next 16.3.8 and React 19.2.4. Its eight existing status-check identities remain the
blocking gate. Production runtime or dependency majors change only in a reviewed PR.

The blocking checks cover locked dependency integrity, compile/import/OpenAPI smoke,
Ruff, full pytest, one-head and downgrade/upgrade migration checks, npm dependency-tree
validation, lint, independent TypeScript, production build, strict dependency audits,
actual Chromium E2E, clean-room Docker preview, and PostgreSQL backup/recovery.

Obsolete skipped browser specs for removed plaintext temporary-password workflows were
deleted rather than counted as coverage. `scripts/check-test-policy.py` fails on any
Python or browser skip/quarantine. Current secure activation, reset, account lifecycle
and audit behavior is covered by `account-access.spec.ts` and backend integration tests.

## Advisory compatibility lane

`compatibility-canary.yml` runs weekly and on manual dispatch. Maintained candidates are
currently Python 3.14 stable, Node 24 LTS, Node 26 Current and PostgreSQL 18 stable.
PostgreSQL 19 remains a prerelease and is excluded from stable lanes. A checked review
deadline makes stale classifications fail visibly instead of remaining frozen. The
workflow prints and validates exact resolved versions; an unavailable or incompatible
candidate fails visibly. It runs:

- locked backend install, `pip check`, compile/import/OpenAPI and focused security,
  token-locking and migration tests on PostgreSQL 18, followed by a disposable
  PostgreSQL 18 `pg_dump`/`pg_restore` round trip with synthetic seed data, restored
  Alembic-head validation and representative integrity checks;
- npm tree/lint/TypeScript/build/audit on Node 24 LTS and Node 26 Current;
- a real FastAPI, Next.js and PostgreSQL 18 journey on Chromium, Firefox and WebKit:
  activation, password reset, generic recovery, login/logout and a protected group
  screen, with listeners registered before first navigation and a 390px overflow check;
- clean-room `--pull --no-cache` image builds.

These scheduled/manual jobs are intentionally separate from the eight PR status checks.
A future-runtime failure creates a maintenance finding but does not silently alter or
invalidate the healthy pinned production lane.

Python prereleases do not have a stable generic selector guaranteed by the setup action.
The manual `python-prerelease` input is the maintained advisory path: supply an explicit
available RC version, which then runs install, compile/import/OpenAPI and deprecation
sentry checks. An unavailable candidate fails rather than being reported as compatible.

## Dependency freshness and the npm exception

Dependabot opens reviewable weekly npm and GitHub Actions PRs; it never auto-merges.
Python remains `requirements.in` → generated `requirements.txt`. The weekly dependency
rehearsal uses pinned `uv==0.9.8` in a disposable checkout, produces an upgraded candidate
lock and diff artifact, installs it in an isolated venv, and runs focused backend tests.
It never commits the candidate lock.

The npm High/Critical gate remains fail-closed. Its only exception is the exact dev-only
`braces` advisory chain under `eslint-config-next@16.3.8`; self-tests verify package,
versions, dependency edges, severity and advisory URL. Remove the exception when that
reviewed chain no longer contains the advisory. Any changed chain or other High/Critical
finding fails.

`npm ls --all` may display unmet platform-specific optional binaries and optional peers
(for example non-Linux SWC/resolver builds, Sass, React Compiler, OpenTelemetry or Jiti).
They are declared optional by their packages; npm returns a valid-tree zero exit status.
Invalid required peers, extraneous required packages, or a nonzero tree result remain
blocking and are not suppressed.

## Release-candidate decision

A deployment candidate requires all of the following evidence:

1. PR CI succeeds 8/8 on the pinned production lane.
2. The PR is reviewed and merged by the authorized maintainer.
3. Post-merge main CI succeeds 8/8 for the exact merge SHA.
4. One Alembic head, previous→head and head→previous→head checks succeed on disposable PostgreSQL.
5. Clean synthetic preview, Chromium critical flows and backup/restore succeed.
6. No unresolved BLOCKER or IMPORTANT acceptance findings remain.
7. The sanitized version-report artifact records the actual pinned runtime/dependencies.
8. Latest compatibility and dependency rehearsal state is visible and any red result is tracked.
9. Production backup protection/location/retention and deployment rollback procedures are approved.
10. Legal/privacy prerequisites (roles, hosting/data location, subprocessors, retention,
    access administration and abuse controls) are independently resolved before real PII.

Automation cannot perform the post-merge decision in advance. A green PR is necessary,
not sufficient, and does not authorize deployment or claim 152-ФЗ compliance.

The security matrix is deliberately scoped to representative protected management,
teacher-group and parent-child reads plus real management and teacher attendance writes.
Its parameterized HTTP cases exercise POST/PATCH and verify persisted PostgreSQL effects
for authorized DIRECTOR/ADMIN and assigned TEACHER actions, while checking forbidden
PARENT/TEACHER mutations, foreign-tenant hiding, unassigned-teacher denial, and blocked
actors. The read matrix additionally covers linked/unlinked parents, archived resources
and revoked relations. It supplements the broader endpoint-specific suite; it does not
claim that every API operation is covered by one matrix.

## Machine-readable report

`python scripts/version-report.py` writes JSON containing the lane plus Python, Node,
PostgreSQL, FastAPI, SQLAlchemy, Alembic, psycopg, Next, React, TypeScript and Playwright
versions. Reports contain no usernames, tenant identifiers, secrets or personal data.
