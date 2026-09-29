# Stage 5 — Operations, Session Cleanup and Pilot Runbooks

Status: implementation record for Issue #115. This document does not change the frozen Stage 1–4 product contract and does not claim full compliance with 152-FZ.

## Authentication-session cleanup

Cleanup is internal and operator-invoked. It is limited to rows in `auth_sessions`; it has no HTTP endpoint or scheduler and adds no datastore or external service.

The only eligibility rule is:

```text
expires_at <= explicit/current UTC cutoff
```

Consequently, expired active and expired revoked sessions are deleted. Revoked sessions whose existing `expires_at` is still in the future are retained, as are active unexpired sessions. Revocation continues to invalidate authentication immediately. Physical deletion waits for the already-existing expiry; there is no second retention duration.

The service returns only an aggregate deleted-row count. It never returns token hashes, user IDs, credentials or PII, and the caller owns the transaction. An exception must propagate, roll the transaction back and produce a non-zero operator command exit.

From `backend/`, with the approved database connection already supplied through the environment and shell tracing disabled:

```bash
python - <<'PY'
from app.db.session import SessionLocal
from app.services.session_cleanup import cleanup_expired_sessions

with SessionLocal.begin() as db:
    deleted_count = cleanup_expired_sessions(db)
print(f"deleted_auth_sessions={deleted_count}")
PY
```

For a controlled historical cutoff, pass a timezone-aware UTC `datetime` explicitly. Never place a database URL, password or other secret in the command or a committed script. Before execution, confirm the target environment and approved access; after execution, retain only the aggregate count and command success/failure. Never log SQL parameters for this operation.

This cleanup must never delete `User`, `Child`, `Guardian`, `Employee`, `Attendance`, `Announcement`, `AuditEvent` or any other business/audit data. Business-data retention and destruction are separate legal/business decisions.

## Availability and deployment verification

1. Confirm the deployed revision is the approved revision and its complete required GitHub CI is green, including backend/frontend, dependency security, browser auth, Docker Compose preview and PostgreSQL backup/recovery gates.
2. Request `GET /api/v1/health` over the deployment's approved HTTPS route.
3. Expect HTTP 200 with exactly `{"status":"ok"}`. The existing handler also executes PostgreSQL `SELECT 1`, so this confirms that the API process can reach the configured database without exposing database details.
4. Do not add credentials, hostnames, detailed database state or contents to the public response. No external monitoring SaaS is selected by this Issue.

If health fails, record only timestamp, deployed revision, safe status/error category and affected environment. Do not record request bodies, cookies, session tokens, password values, secret keys, credential-bearing URLs or PII. Stop rollout/traffic expansion, notify the responsible operator, distinguish API/process failure from PostgreSQL/connectivity failure using protected infrastructure telemetry, recover through the approved deployment/database procedure, repeat the health check and relevant required CI, and document the privacy-safe outcome.

## Incident and failure response

Use this sequence for service, PostgreSQL, authentication/session and suspected cross-tenant/access-control incidents:

1. **Detect and classify.** Establish time, environment, revision, affected capability and safe aggregate scope. Treat suspected unauthorized access or tenant-boundary failure as a security/privacy incident.
2. **Contain.** Stop rollout, isolate the affected component or restrict access using approved infrastructure controls. Do not destroy evidence and do not improvise schema, auth or tenant changes.
3. **Escalate.** Notify the named incident owner and the current security/privacy/legal contacts through the approved channel. Legal notification duties and timing require current specialist judgment.
4. **Preserve safe evidence.** Preserve access-controlled deployment metadata, aggregate counters, sanitized errors and relevant audit records. Never collect or copy request-body PII, cookies, session tokens, password values, secret keys or credential-bearing URLs. Record who accessed the evidence.
5. **Recover.** Use the approved deployment rollback or PostgreSQL recovery runbook. For an authentication/session incident, revoke affected sessions through the existing auth behavior; do not physically delete unexpired revoked rows. For suspected cross-tenant access, keep the service contained until tenant boundaries are understood.
6. **Verify.** Repeat health and required CI/deployment checks. After auth, database recovery or any suspected access-control incident, explicitly re-verify login/logout/revocation, RBAC and tenant isolation before reopening access.
7. **Review.** Record cause, containment, evidence handling, recovery evidence, decisions, owners and follow-up actions without sensitive payloads.

### Service or PostgreSQL failure

Freeze rollout, determine whether the API process, database availability or connectivity is responsible, protect data from conflicting writes, and restore only through the approved deployment or PostgreSQL operational path. A failed health response is not proof of data loss. After recovery, check `GET /api/v1/health`, execute applicable application smoke checks, and re-verify auth/tenant boundaries when database state may have changed.

### Backup or recovery failure

Stop claiming recoverability. Preserve privacy-safe command status and error category, protect the backup artifact and access controls, notify the responsible operator, repair the cause, and repeat the full disposable synthetic backup/restore verification. Never move production data into development, test, preview or recovery-verification environments. Do not resume a recovery claim until verification and required CI are green.

## Pilot unresolved checklist

Before real personal data or a real pilot, the pilot owner must explicitly resolve and record:

- operator/controller and processor roles and responsibilities;
- hosting architecture, jurisdiction and data location;
- subprocessors and complete data flows;
- business-data retention and destruction rules;
- access administration, least privilege, periodic review and prompt revocation;
- backup protection, access, location and retention;
- current legal/privacy specialist review, including applicable 152-FZ requirements.

Development, test, preview and disposable recovery use synthetic data only. No cloud/vendor monitoring solution is selected here. Technical tests, runbooks and recovery evidence do not establish full 152-FZ compliance.
