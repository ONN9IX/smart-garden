# Stage 10 — Protected Storage API and Security

**Status:** design proposal for Issue #144; frozen only after the design PR merges.
**Owner:** ONN9IX.
**Implementation:** NOT AUTHORIZED until Stage 6 integrated acceptance is complete.
**Conventions:** /api/v1, JSON snake_case, UUID identifiers, server-owned tenant/actor fields.

## 1. Security boundary

Protected storage is an internal infrastructure service.

It does not expose a generic user-facing list-all-files, upload-arbitrary-file, download-by-ProtectedObject-UUID, or delete-arbitrary-file API.

Every HTTP route remains domain-specific.

## 2. Authorization order

For every content read:

1. authenticate User;
2. derive tenant;
3. load tenant-scoped domain object;
4. evaluate domain-specific role/assignment/participant/Guardian authorization;
5. resolve the domain object's protected_object_id;
6. load same-tenant ProtectedObject;
7. verify status and kind;
8. stream bytes.

Never reverse this order by loading arbitrary ProtectedObject first and guessing domain ownership.

## 3. Domain content routes

Stage 10 does not replace frozen domain routes.

Photos continue to authorize through PhotoAsset/consent routes such as teacher/photos/{photo_id}/content and parent/photos/{photo_id}/content.

Contracts continue to use the frozen Stage 7 contract document routes.

Receipts continue to use the frozen Stage 7 receipt content routes.

No /protected-objects/{id}/content route is available to ordinary users.

## 4. Internal ProtectedObject model

Conceptual fields:

- id
- organization_id
- kind
- backend_code
- object_key
- mime_type
- size_bytes
- sha256
- status
- retention_class
- created_by
- created_at
- available_at
- removed_at

Constraints should include:

- positive size;
- SHA-256 format;
- allowed status/kind/backend enums;
- unique backend/object key;
- immutable content metadata after available, except lifecycle timestamps/status;
- tenant ownership.

## 5. Domain reference integrity

Each domain reference must prove kind compatibility.

Examples:

- PhotoAsset may reference only kind=photo;
- ContractVersion document only kind=contract_document;
- Receipt document only kind=receipt_document.

Implementation may enforce this in service logic and tests and add database constraints where practical.

## 6. Upload workflow

Domain service performs business authorization first.

Then storage workflow:

1. enforce requested kind from server-side domain path;
2. reject unsupported body/media;
3. stream/read with hard size limit;
4. validate content;
5. sanitize/normalize when required;
6. compute SHA-256;
7. scan when required;
8. generate opaque object key;
9. write immutable bytes through adapter;
10. persist ProtectedObject metadata;
11. link domain record transactionally;
12. return domain response without object key.

Do not accept kind, organization_id, object_key, backend_code, or created_by from ordinary clients as authority.

## 7. Two-phase safety

Database and object storage do not share one transaction.

Approved implementation strategies may use temporary object promotion or final-object write plus deterministic orphan cleanup.

Whichever strategy is selected must guarantee:

- no domain row claims unavailable bytes are ready;
- no unbounded orphan accumulation;
- cleanup is tenant-safe;
- retries do not attach another tenant's object.

## 8. Idempotency

A retry after uncertain upload result must not silently attach multiple documents where the domain permits only one current object.

Use domain-level version/replacement semantics and, where required, an idempotency key scoped to authenticated tenant, actor/domain command and target domain object/version.

Raw SHA-256 is not globally authoritative for deduplication.

## 9. Download response

Default application-mediated response is:

- authenticated;
- streamed;
- correct validated MIME type;
- safe generated filename;
- Content-Disposition appropriate to domain;
- Cache-Control: private, no-store;
- X-Content-Type-Options: nosniff where supported;
- no object key/provider URL.

## 10. Range requests

Range streaming is optional and not required for Stage 10 core.

If added later:

- authorization occurs before range processing;
- requested range is bounded;
- backend behavior is tested;
- no direct provider URL bypass.

## 11. Initial content allowlist

Photo:

- image/jpeg
- image/png

Contract document:

- application/pdf

Receipt document:

- application/pdf

Do not add SVG, HTML, JavaScript, Office macros, archives, or executable formats without separate content-security review.

## 12. Image sanitizer

The image pipeline must:

- decode supported content;
- reject malformed/mismatched files;
- remove unneeded metadata including GPS/EXIF where technically possible;
- prevent embedded metadata from reaching logs/Audit;
- enforce pixel/dimension/resource limits against decompression bombs.

Existing Stage 6 photo protections should be preserved or strengthened.

## 13. PDF validation

PDF upload must:

- satisfy size cap;
- match expected PDF content validation;
- pass approved malware scanning in production before available;
- not rely only on extension or browser MIME.

Stage 10 does not claim to sanitize arbitrary active PDF content. Unsafe content is rejected/quarantined.

## 14. Malware scanner adapter

Conceptual scanner returns:

- clean;
- infected;
- error.

Production general-document availability requires clean.

Scanner details and raw findings are not exposed to ordinary API clients.

Scanner vendor is not selected by Issue #144.

## 15. Storage adapter

Conceptual operations:

- put immutable bytes/stream;
- open/read;
- stat/verify;
- delete under approved lifecycle;
- health/readiness.

Adapter receives server-generated internal keys.

Vendor SDK types must not leak into domain schemas.

## 16. Production disabled adapter

Before a production provider is approved, production configuration fails closed.

Upload/read requiring unavailable production storage returns a safe structured error such as PROTECTED_STORAGE_UNAVAILABLE.

Do not silently fall back to a public or temporary local directory in production.

## 17. Local development adapter

Allowed only outside production.

Requirements:

- private configured directory;
- no public web-server mount;
- generated opaque filenames;
- same domain authorization/API contract;
- synthetic files only;
- deterministic test cleanup.

## 18. Secrets

Storage/scanner credentials belong in approved secret infrastructure.

Never store them in ProtectedObject, domain tables, Git, browser-visible env, Audit, or fixtures.

## 19. Tenant key isolation

Internal keys should include opaque environment/tenant separation for operations and cleanup.

They must not include Child name, Guardian name, phone, contract text, or original filename.

The key structure is not an authorization mechanism.

## 20. Object existence privacy

Before domain authorization, do not reveal whether a ProtectedObject exists, its backend, size/hash, tenant, or quarantine state.

Foreign domain UUIDs follow current non-disclosure behavior.

## 21. Audit

Storage infrastructure should not generate noisy business Audit for every low-level byte read unless domain requirements demand it.

Domain actions remain authoritative.

Audit may include protected object UUID when useful, but never object key, provider URL, raw filename containing PII, bytes, scanner raw output, or secret.

## 22. Technical logs

Allowed:

- request/correlation ID;
- protected object UUID after authorization where needed;
- kind;
- byte count;
- safe backend code;
- operation result;
- timing.

Avoid original filename, object key, signed URL, response bytes, document text, image metadata, and PII.

## 23. Quarantine

Quarantined content is not available to ordinary users.

Any future operations-only quarantine screen may show only safe metadata and scanner result code. It must not make suspicious bytes downloadable through normal staff UI.

## 24. Removal boundary

Ordinary users do not call a generic ProtectedObject DELETE endpoint.

Domain services control lifecycle:

- photo removed/restricted;
- contract version replaced while history is retained;
- receipt replacement keeps history.

Physical purge belongs to retention-policy infrastructure.

## 25. Backup and replication

Database backup includes ProtectedObject metadata, not automatically the object bytes.

Production provider design must define object replication, backup, restore, integrity checks, deletion propagation and environment binding.

A restored database must fail closed rather than accidentally point to another environment's object bucket.

## 26. Environment isolation

Development, test, preview and production storage are strictly separated.

Never allow dev/preview/test to read or clean production storage.

Environment mismatch fails closed.

## 27. Required negative tests

Authorization:
- direct ProtectedObject UUID content route absent for ordinary users;
- foreign tenant domain object denied;
- wrong role denied;
- unassigned TEACHER photo denied;
- non-entitled PARENT contract/receipt denied;
- withdrawn photo consent denied.

Upload:
- unsupported MIME rejected;
- extension spoof rejected;
- oversized file rejected;
- malformed image/PDF rejected;
- executable/archive rejected;
- production without storage/scanner fails closed.

Privacy:
- no public URL/object key in response;
- body absent from Audit/logs;
- photo metadata stripped;
- original filename not used as object key;
- private/no-store content response.

Integrity:
- hash matches final stored bytes;
- replacement creates new object;
- old bytes unchanged;
- partial failure cannot produce false available state;
- orphan cleanup is tenant/environment safe.

## 28. Required integration tests

Future implementation must cover:

1. photo upload → protected object → authorized teacher/parent read;
2. photo consent withdrawal → read denied;
3. contract PDF attach → authorized Stage 7 read;
4. receipt PDF attach → authorized Stage 7 read;
5. replacement history;
6. foreign tenant/role denial;
7. unavailable backend behavior;
8. synthetic-only content.

## 29. Compatibility

Stage 10 preserves existing auth/session, tenant isolation, Stage 6 photo consent, Stage 7 contract/receipt entitlement, Audit privacy, and Stage 5 backup/security controls.

The storage abstraction may change where bytes live; it may not widen who can read them.