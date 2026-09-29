# Stage 5 — Operations and Pilot Design

Status: **FROZEN** by Issue #103 / PR #105 at design baseline `3ba76177d27c4ae62092e85acfefb456daf510f4`. This document defines later operational deliverables and pilot gates. Any future design change requires a new explicit Master Chat decision.

## Backup and restore

The pilot recovery path uses PostgreSQL-native backup and restore tools. No cloud backup vendor is selected in Stage 5 design.

Required properties:

- backup credentials and secrets come from the execution environment and are never embedded in scripts;
- backup output is checked for command success and basic integrity before being accepted;
- restore runs only against an explicitly identified disposable/synthetic target;
- destructive restore actions require explicit target validation and a documented guard/confirmation mechanism;
- production data is never copied into dev, test, preview or recovery-verification environments;
- restore verification checks database availability, expected schema/migration compatibility and representative synthetic Stage 1–4 records;
- verification produces privacy-safe evidence suitable for CI or an operator runbook;
- failure leaves an actionable safe diagnostic and cannot be reported as a successful recovery.

The recovery runbook must state prerequisites, backup, validation, restore, migration-compatibility check, application verification, failure handling and cleanup. Actual production recovery additionally requires approved infrastructure, access and retention decisions.

## Monitoring and operations

Pilot operations must define:

- service availability checks based on the existing health capability;
- PostgreSQL availability checks that do not expose credentials or database contents;
- deployment verification and linkage to required CI evidence;
- privacy-safe technical logging and redaction rules;
- an incident-response checklist with detection, containment, escalation, evidence protection, recovery and review;
- backup failure response: stop claiming recoverability, preserve safe diagnostics, notify the responsible operator, repair and repeat verification;
- service failure response: determine scope, protect data, restore service through the documented path, verify tenant/auth boundaries and record the outcome.

No external monitoring or error-tracking SaaS is selected by default. Adding one requires a Master Chat decision plus privacy, subprocessor and data-flow review.

## Retention

Stage 5 may automate cleanup only for ephemeral authentication/session data: expired sessions and revoked sessions after a documented technical retention window.

Stage 5 does not define deletion periods for Child, Guardian, Employee, Attendance, Announcement or Audit data. Their retention and destruction rules remain an explicit legal/business decision for pilot readiness. Session cleanup must never delete business audit events.

## Pilot privacy and 152-FZ checklist

Before any real personal data is used, the pilot owner must separately confirm and record:

- operator and processor roles;
- hosting architecture and data location;
- subprocessors and complete data flows;
- business-data retention and destruction rules;
- access administration, least privilege and revocation process;
- incident detection, escalation and response process;
- backup access, encryption/protection, location and retention;
- current legal/privacy specialist review of applicable requirements.

Dev, test, preview and disposable recovery verification use synthetic data only. No speculative PII fields are permitted.

**Technical Stage 5 acceptance is not proof of full legal compliance with 152-FZ.** Legal readiness for a real pilot requires a current specialist review and explicit resolution of the checklist above.

## Pilot operational gate

Operations are pilot-ready only when backup and restore have been executed successfully with synthetic data, monitoring and incident procedures are reproducible, session cleanup is bounded and verified, required CI/deployment checks are green, operators know the escalation path, and all unresolved legal/infrastructure decisions are visible rather than treated as technically complete.
