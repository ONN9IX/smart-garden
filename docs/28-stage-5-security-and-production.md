# Stage 5 — Security and Production Design

Status: **FROZEN** by Issue #103 / PR #105 at design baseline `3ba76177d27c4ae62092e85acfefb456daf510f4`. This is the production/security contract for later Stage 5 implementation Issues; it does not itself authorize implementation. Any future design change requires a new explicit Master Chat decision.

## Production configuration

Shared environments (staging and production) must fail closed.

- They require explicitly supplied strong secret configuration. Unsafe, missing or placeholder values block startup.
- The session cookie remains HttpOnly and must also be Secure in shared environments.
- Allowed origins are explicit per environment. Wildcard CORS is forbidden.
- Localhost and other development defaults must never be inherited silently by staging or production.
- Existing server-side Origin enforcement for state-changing requests remains active and must not be weakened by shared-environment configuration.
- Production secrets must not be committed, embedded in images, scripts, documentation or logs.
- Configuration failures must report a safe diagnostic that does not reveal secret values.

Future implementation may add only the minimal configuration fields and validation needed to enforce these invariants. It must not redesign auth, tenant derivation or RBAC.

## Login abuse protection

The pilot requires a documented, testable brute-force/login-abuse control. Prefer enforcement at the pilot deployment or reverse-proxy boundary when that topology supports a reliable per-source and/or per-account policy.

The selected control must define:

- protected login route and counting key(s);
- limit/window and rejection behavior;
- trusted-proxy/client-address handling;
- safe operational visibility without passwords, request bodies or unnecessary PII;
- a repeatable verification procedure in the selected pilot topology;
- recovery/escalation steps for false positives or abuse.

An in-memory application counter must not be presented as a multi-instance security guarantee. No new datastore may be added solely for rate limiting without a Master Chat architecture decision. If the chosen deployment boundary cannot provide a dependable control and a new datastore or auth redesign appears necessary, implementation must STOP and return to Master Chat.

## Sessions

The current server-side session model, HttpOnly cookie and revocation behavior remain authoritative. Stage 5 may add an internal operational cleanup path for:

- expired sessions;
- revoked sessions after a documented technical retention window.

Cleanup must be tenant-safe where tenant context applies, idempotent, observable through privacy-safe technical counts and unavailable as a public API. It must not delete business audit events or business data. The technical retention window must be justified operationally and must not be reused as a business-data retention decision.

## CSRF and Origin

The current exact-Origin plus SameSite approach is preserved. A new CSRF-token architecture is not introduced unless a concrete Stage 5 finding demonstrates that the selected deployment topology makes the existing protection insufficient. Proxy and origin configuration must preserve the server-side exact-Origin checks.

## Safe logging

Production and pilot logs may contain only the minimum technical information needed for availability, diagnosis and incident handling. They must not contain:

- request bodies with PII;
- passwords or temporary passwords;
- session tokens or cookie values;
- authentication or application secrets;
- unnecessary identifiers or query values that expose personal data.

Errors must use safe structured context and redaction. Browser storage, URLs and client telemetry must not become alternate channels for credentials, tokens or PII. External error tracking, analytics and session replay are not selected by this design.

## Verification and escalation

Later implementation Issues must provide targeted tests for configuration invariants and security behavior plus deployment-level evidence for controls owned by the reverse proxy/platform. Required CI remains unchanged unless a separately scoped CI Issue explicitly maintains it.

Any need to add an external service/datastore, redesign authentication or RBAC, weaken Origin/CORS/cookie protections, or change tenant derivation is a STOP condition requiring Master Chat review.
