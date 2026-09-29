# Stage 5 — Design and Decisions

Status: **FROZEN** by Issue #103 / PR #105 at design baseline `3ba76177d27c4ae62092e85acfefb456daf510f4`. Any future design change requires a new explicit Master Chat decision.

## Goal

Stage 5 prepares the accepted Stage 1–4 MVP for a controlled pilot through production, security, recovery, operations, supply-chain and acceptance hardening. It does not add a new end-user product module. Stages 1–4 remain FROZEN.

## Scope

In scope:

- fail-closed production configuration and pilot security hardening;
- auth/session hardening that preserves the current authentication architecture;
- CI, toolchain and supply-chain maintenance without weakening required gates;
- PostgreSQL-native backup, restore and disposable recovery verification;
- availability checks, safe logging, incident procedures and pilot runbooks;
- technical cleanup of ephemeral expired/revoked session data;
- a current privacy, legal, infrastructure and data-flow checklist for the pilot;
- onboarding reconciliation, complete regression and Stage 5 acceptance.

Out of scope:

- TEACHER, a full PARENT UI, SCUD/tablets/biometrics/cameras;
- payments, files/documents/photos, push/email/SMS, chat, analytics/trends or AI;
- speculative business or PII fields;
- changes to frozen Stage 1–4 business/API contracts without a confirmed Stage 5 security or production finding;
- a declaration of full legal compliance with 152-FZ.

## Frozen architecture

Stage 5 preserves:

- Next.js / React / TypeScript frontend;
- FastAPI / Python backend;
- PostgreSQL as the only database;
- SQLAlchemy and Alembic;
- `/api/v1`, JSON `snake_case` and UUID identifiers;
- server-side sessions, HttpOnly cookie and Argon2id password hashes;
- tenant derivation only from the authenticated User;
- current tenant isolation and DIRECTOR / ADMIN / PARENT RBAC.

The following are not introduced by default: Redis, a second database, an external authentication provider, foreign analytics, session replay, external monitoring SaaS or a new secret manager.

## Change authority

Allowed implementation is limited to work explicitly assigned by a Master Chat Issue with an exact baseline, owner, scope, write-set, validation and merge order. Minimal configuration, scripts, tests, CI/toolchain maintenance and operational documentation needed to meet this Stage design are permitted in their future Issues.

A separate Master Chat architecture decision is required before:

- redesigning auth, sessions, RBAC, tenant derivation, API or database architecture;
- adding any datastore, external service, monitoring/analytics system, auth provider or secret manager;
- changing a frozen Stage 1–4 business contract;
- introducing a new PII field, data flow or processor;
- assigning two parallel Issues an overlapping or shared/high-conflict write-set.

## Privacy and security boundaries

Every Stage 5 decision and implementation must review PII necessity, data minimization, tenant isolation, RBAC, auth/session impact, API exposure, logs, URLs, browser storage, audit, retention, backup, test data and infrastructure data flows.

- Dev, test, preview and recovery verification use synthetic data only.
- Request bodies containing PII, credentials, session tokens, cookies and auth secrets must not be logged.
- Business-data retention periods are not invented in Stage 5.
- Audit events are not deleted by session cleanup.
- Technical Stage 5 acceptance is not proof of full legal compliance with 152-FZ.

## Acceptance concept

Stage 5 can be accepted only after all Master Chat-assigned delivery waves are complete. Acceptance evidence must include:

1. fail-closed shared-environment configuration and documented, testable login-abuse protection;
2. verified PostgreSQL backup/restore against a disposable synthetic environment;
3. operational checks, safe logging rules and incident/recovery runbooks;
4. supported CI/toolchain/supply-chain checks with existing required gates preserved;
5. documented session cleanup limited to ephemeral auth/session data;
6. completed technical privacy/legal/infrastructure pilot checklist with unresolved legal/business decisions stated explicitly;
7. full required PostgreSQL, migration, frontend, real-browser and Docker preview regression evidence;
8. no open BLOCKER or CURRENT STAGE findings;
9. final acceptance document, `docs/CURRENT_STATE.md` reconciliation and Master Chat freeze decision.

## Return to Master Chat

Stop the assigned Issue and return to Master Chat if work requires a file outside its write-set, changes a frozen contract, redesigns auth/RBAC/tenant/database architecture, needs a new external service or datastore, exposes a security/privacy architecture conflict, conflicts with Issue #102 or reveals a BLOCKER/CURRENT STAGE finding. Do not resolve such a decision inside a developer branch.
