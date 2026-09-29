# Stage 5 — Production Security Implementation

Issue #106 implements the frozen Stage 5 production-configuration contract. It preserves server-side sessions, HttpOnly cookies, the SameSite and exact-Origin model, Argon2id, authenticated-user tenant derivation and DIRECTOR / ADMIN / PARENT RBAC. No new datastore, auth provider, CSRF-token architecture or external security service is introduced.

## Shared-environment configuration

Staging and production fail closed unless they receive an explicit strong `SECRET_KEY` and a non-empty set of explicit CORS origins. Shared environments reject short, predictable or placeholder secrets and reject wildcard, malformed, localhost, loopback and unspecified-bind origins. PostgreSQL remains the only database, and session cookies remain Secure in staging and production. Development and test retain intentional local defaults.

No secret values, credentials, request bodies, session tokens, cookies or real PII are logged or committed.

## Pilot login-abuse contract

The pilot protects `POST /api/v1/auth/login` at the deployment/reverse-proxy boundary when the selected pilot topology can enforce the following contract reliably across all application instances.

### Counting and dimensions

- Count failed and excessive login attempts for the protected route.
- Apply a source dimension derived from the verified client address and an account dimension derived from a privacy-safe, one-way normalized account key.
- Do not store or emit submitted passwords, request bodies, raw cookies, session tokens or unnecessary account identifiers.
- A source-only rule must not be the sole protection where many legitimate users may share an address; the final pilot policy must combine dimensions and document its limits.

The exact thresholds and windows belong to the selected pilot deployment configuration and must be recorded before pilot acceptance. This repository does not claim an in-memory application counter is multi-instance safe.

### Trusted proxy and client address

The deployment must define the complete trusted-proxy chain. Forwarded client-address headers are accepted only from those trusted hops; direct or untrusted clients must not be able to choose the counted source address. The verifier must prove both the normal proxy path and a spoofed-header attempt.

### Rejection and visibility

- When a limit is exceeded, reject the login request at the boundary with HTTP `429` and a generic response that does not disclose whether an account exists.
- Apply a bounded retry delay or `Retry-After` behavior documented by the selected deployment.
- Emit only aggregate privacy-safe technical metrics: protected route, rule identifier, outcome and coarse source/account-key counts needed for operations.
- Do not log the request body, password, temporary password, raw username, cookie, session token or secret.

### Repeatable verification

Before a real pilot, run a deployment-level test against a disposable environment with synthetic accounts:

1. send allowed login attempts through the normal trusted-proxy path and confirm normal auth behavior is unchanged;
2. exceed the documented source limit and confirm HTTP `429` without an account-existence signal;
3. exceed the account-key limit from more than one synthetic source and confirm consistent enforcement;
4. attempt to spoof forwarding headers from an untrusted path and confirm the attacker cannot select the counted address;
5. wait for or administratively clear the documented window and confirm recovery;
6. inspect operational output and confirm it contains no request bodies, credentials, tokens, cookies or raw account identifiers;
7. repeat against every application instance or ingress path used by the pilot.

The evidence must name the deployment topology and rule version while containing synthetic data only.

### False positives and recovery

Operators must be able to identify the triggered rule from privacy-safe metadata, confirm whether a shared source caused the block and use a documented time-bounded recovery action. Any temporary exception must be least-privilege, recorded, reviewed and removed after recovery. Operators must not disable the complete control or expose whether a username exists.

If the selected pilot topology cannot enforce this contract reliably without a new datastore or service, implementation must stop and return an architecture decision to Master Chat. No vendor or production hosting platform is selected by this Issue.

## Privacy boundary

All validation uses synthetic data. This technical hardening does not prove full legal compliance with 152-FZ; real-pilot readiness still requires the current legal, privacy, infrastructure and data-flow review defined by the frozen Stage 5 design.
