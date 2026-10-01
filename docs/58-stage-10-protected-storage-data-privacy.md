# Stage 10 — Protected Storage Data, Privacy and 152-FZ Boundary

**Status:** design proposal for Issue #144; frozen only after the design PR merges.
**Owner:** ONN9IX.
**Scope:** technical privacy/security design only.
**Implementation:** NOT AUTHORIZED until Stage 6 integrated acceptance is complete.

## 1. Boundary

Protected binary content can contain significantly more personal information than ordinary structured UI fields.

Examples:

- child photos;
- signed contracts;
- receipt/fiscal documents;
- future approved documents.

Stage 10 therefore treats all protected objects as private tenant data even when a particular file appears harmless.

Technical design does not by itself establish full 152-FZ compliance or authorize real production files.

## 2. Data minimization

Store only metadata necessary to operate secure storage:

- object UUID;
- tenant;
- approved object kind;
- internal backend/key;
- MIME;
- size;
- SHA-256;
- lifecycle status;
- retention class identifier;
- creator reference where justified;
- timestamps.

Do not duplicate domain PII into storage metadata.

In particular, ProtectedObject does not need:

- Child name;
- Guardian name;
- phone/email;
- contract text;
- payment details;
- diary/message content.

## 3. Content sensitivity

### Photos

May visually identify Children and reveal context about attendance, group membership or location.

Treat as sensitive private content.

### Contract documents

May contain legal and identity information beyond structured Contract metadata.

Treat as restricted legal/private content.

### Receipts

May contain financial/payment/fiscal details.

Treat as restricted financial/private content.

The storage layer does not need to inspect or index semantic document text for product use.

## 4. No unrestricted indexing

Do not:

- full-text index contract/receipt contents;
- OCR protected documents by default;
- run image recognition;
- create face embeddings;
- send content to AI;
- make content searchable by public or cross-tenant systems.

Any future content extraction requires its own privacy/design gate.

## 5. Hosting and localization

Issue #144 does not choose a production provider, region or jurisdiction.

Before real files are stored, Master Chat and deployment/legal review must explicitly approve:

- provider;
- physical/data region;
- localization requirements;
- subprocessors;
- backup/replication locations;
- cross-border data flows if any;
- provider contract/security terms.

Production storage remains fail-closed until this decision exists.

## 6. Encryption at rest

Production provider selection must provide an approved encryption-at-rest design.

The design must specify:

- encryption mechanism;
- key ownership;
- key rotation;
- administrator access;
- backup encryption;
- restore behavior.

Stage 10 does not invent a KMS/vendor.

For especially restricted future identity documents, application/field/object-level encryption may require a separate design beyond provider default encryption.

## 7. Encryption in transit

Production upload/download requires HTTPS/TLS under approved deployment architecture.

Backend-to-storage/scanner communication must use authenticated encrypted transport appropriate to the selected providers.

Do not send protected bytes over unauthenticated transport.

## 8. Secrets and keys

Provider/scanner credentials are secrets, not business data.

Never place them in:

- database object metadata;
- source repository;
- frontend bundle;
- URL query;
- Audit;
- logs;
- screenshots;
- test fixtures.

Secret rotation must not require rewriting domain business objects.

## 9. Authorization and privacy

Storage never decides user entitlement from object metadata alone.

Domain authorization remains authoritative.

Examples:

- photo read requires current Stage 6 consent/participant rules;
- contract document read requires Stage 7 role/contracting-Guardian entitlement;
- receipt read requires Stage 7 financial entitlement.

This prevents storage abstraction from accidentally widening access.

## 10. Object key privacy

Internal object keys are confidential operational identifiers.

They must:

- be server-generated;
- avoid PII;
- remain absent from ordinary API responses;
- never be treated as bearer credentials.

If exposed accidentally, the key still must not be sufficient to read bytes without provider/backend authorization.

## 11. Public URLs

Permanent public URLs are forbidden.

Do not:

- mount the storage directory under static web root;
- return provider public URLs;
- embed public bucket paths in frontend models;
- use guessable object URLs.

Application-mediated authenticated streaming is the default core.

## 12. Signed URL privacy

Signed URLs are deferred.

If later approved, review:

- expiry;
- referrer leakage;
- browser history;
- copy/share risk;
- provider logs;
- CDN behavior;
- revocation;
- caching.

Signed URL support must not become a permanent link.

## 13. Browser cache/storage

Protected bytes and metadata must not be persisted by application code in:

- localStorage;
- sessionStorage;
- IndexedDB;
- offline service-worker caches.

Sensitive responses use private/no-store behavior.

The browser may temporarily hold bytes necessary to render/download within the active authorized session.

## 14. Original filenames

Original filenames can contain personal data.

Default rule:

- do not persist original filename;
- do not log it;
- do not use it as object key.

Generate safe download names from non-sensitive domain identifiers after authorization.

If a future workflow requires preserving a filename, it needs field-specific privacy review and strict normalization.

## 15. Image metadata

Do not intentionally preserve EXIF/GPS/camera metadata.

Photo sanitizer should remove metadata not required by Smart Garden.

This reduces accidental disclosure of:

- location;
- device information;
- author comments;
- embedded text metadata.

## 16. Malware scanning privacy

Scanner receives content only under the approved production data-flow agreement.

Before selecting a scanner/provider, review:

- where bytes are processed;
- retention by scanner;
- telemetry;
- subprocessors;
- region;
- raw sample retention;
- false-positive support workflow.

Raw scanner output should not contain or reproduce document content in ordinary logs/Audit.

## 17. Quarantine

Quarantined objects remain private.

Ordinary DIRECTOR/ADMIN/TEACHER/PARENT users do not get a download path for quarantined bytes.

Operations tooling should use minimal metadata and safe result codes.

## 18. Logs

Never log:

- file body;
- contract text;
- receipt text;
- image bytes;
- EXIF;
- provider signed URL;
- storage secret;
- scanner raw payload;
- original filename by default.

Allowed minimal operational metadata may include:

- request ID;
- object UUID;
- kind;
- size;
- safe backend code;
- safe outcome;
- timing.

Logs still follow tenant and production retention controls.

## 19. Audit

Business Audit records the domain action, not file body.

Examples:

- photo.create;
- contract document attach/replace;
- receipt register/replace.

Audit details must not contain:

- object key;
- public/signed URL;
- file bytes;
- extracted text;
- scanner raw result;
- sensitive original filename.

Restricted identity document access, if ever introduced, requires its own read-Audit policy.

## 20. Retention classes

ProtectedObject stores a retention-class identifier, not an invented legal duration.

Examples of conceptual classes:

- photo_content;
- contract_legal_document;
- fiscal_receipt.

The actual duration/destruction trigger is a pre-pilot business/legal decision.

Do not hard-code speculative legal periods in Stage 10.

## 21. Removal vs destruction

Distinguish:

- domain no longer displays content;
- ProtectedObject status removed;
- storage object physically purged;
- backups/replicas aged out.

A UI “remove” action must not falsely claim all copies are legally destroyed.

Physical purge requires approved retention and operational process.

## 22. Backups

Protected bytes require a production backup/replication decision separate from PostgreSQL metadata backups.

Before real pilot define:

- whether provider replication is backup;
- backup region;
- encryption;
- restore testing;
- retention;
- delete propagation;
- operator access.

Do not copy production object storage into dev/test.

## 23. Restore

Restore procedure must preserve environment and tenant boundaries.

A production database restored into another environment must not automatically gain access to the production object bucket unless explicitly authorized.

Environment binding should fail closed.

## 24. Dev/test/preview

Synthetic files only.

Use:

- generated test images;
- clearly fake PDF contracts;
- clearly fake receipt PDFs.

Do not use:

- real children photos;
- real signed contracts;
- real passports;
- real fiscal receipts;
- production object dumps.

## 25. Support/debug workflow

Support staff should troubleshoot using:

- object UUID;
- safe domain identifier;
- status;
- size/hash;
- safe error code.

Do not ask users to paste storage credentials or sensitive document contents into tickets/logs.

Any privileged support access to actual restricted content requires an explicit operational/access policy.

## 26. Analytics and AI

No protected content is sent to:

- product analytics;
- session replay;
- external AI;
- image recognition;
- OCR;
- document extraction

without a new explicit privacy/design decision.

Metadata analytics also require minimization and tenant isolation.

## 27. Subject access/export

Future personal-data export/subject request handling must go through domain authorization and legal process.

Storage layer does not expose a bulk tenant object dump to ordinary users.

Export must preserve:

- other children's privacy;
- other Guardians' privacy;
- financial entitlement;
- document history rules.

## 28. Incident response

Before real storage pilot define operational response for:

- leaked credential;
- public-bucket misconfiguration;
- malware upload;
- object corruption;
- unauthorized access;
- provider outage;
- lost backup;
- suspected cross-tenant exposure.

Technical controls do not replace an organizational incident process.

## 29. Required privacy tests

Future implementation must verify:

1. foreign tenant cannot read object through any domain.
2. direct ProtectedObject UUID is not sufficient for download.
3. object key absent from ordinary response.
4. no public URL.
5. file body absent from Audit/logs.
6. original filename not used in object key.
7. photo metadata sanitized.
8. browser application storage contains no protected bytes.
9. dev/test fixtures are synthetic.
10. production without approved provider/scanner fails closed.
11. environment mismatch fails closed.
12. quarantine content cannot be downloaded through normal UI.

## 30. Pre-pilot unresolved decisions

Required before real PII/files:

- storage provider;
- data region/localization;
- scanner provider;
- provider/subprocessor contracts;
- encryption/key management;
- retention/destruction;
- backup/replication;
- admin/support access;
- monitoring/incident response;
- secret rotation;
- subject/export process.

## 31. Acceptance boundary

A green technical Stage 10 acceptance proves the software follows the frozen private-storage contract.

It does not by itself prove legal compliance or authorize real production photos/contracts/receipts.