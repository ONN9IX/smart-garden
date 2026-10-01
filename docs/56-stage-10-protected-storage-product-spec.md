# Stage 10 — Protected Storage Product Specification

**Status:** design proposal for Issue #144; frozen only after the design PR merges.
**Owner:** ONN9IX.
**Implementation:** NOT AUTHORIZED until Stage 6 integrated acceptance is complete.
**Design baseline:** `4993d3e1f3128b8a1f23c7d7c085084b062fc6b8`.

## 1. Goal

Create one private binary-content architecture for Smart Garden instead of letting Photos, Contracts and Receipts invent separate storage patterns.

The target flow is:

```text
domain authorization
→ validate file
→ sanitize / scan
→ store immutable bytes
→ persist protected-object metadata
→ domain record references object
→ every read re-authorizes domain access
→ authenticated stream
```

Stage 10 is infrastructure for approved product domains, not a generic user file drive.

## 2. Product principles

1. Private by default.
2. No permanent public URL.
3. Storage object identity is never authorization.
4. Domain authorization happens before every upload/read.
5. Tenant is derived only from authenticated User/domain object.
6. Bytes become immutable when available.
7. Replacement creates a new object.
8. File content never enters Audit/logs/analytics.
9. Dev/test/preview use synthetic content only.
10. Production provider selection is separate from this design.

## 3. Initial protected object kinds

Stage 10 core supports only explicitly approved kinds:

- `photo`
- `contract_document`
- `receipt_document`

Future kinds require an explicit design/privacy review.

Do not expose a generic `kind=anything` upload API.

## 4. Shared metadata concept

Freeze one provider-neutral metadata entity: `ProtectedObject`.

Conceptual fields:

- `id: UUID`
- `organization_id: UUID`
- `kind: enum`
- `backend_code: string/enum`
- `object_key: opaque string`
- `mime_type: string`
- `size_bytes: integer`
- `sha256: string`
- `status: pending_scan | available | quarantined | unavailable | removed`
- `retention_class: string/enum`
- `created_by: UUID | null`
- `created_at`
- `available_at: timestamp | null`
- `removed_at: timestamp | null`

Optional implementation fields may be added only when required by the approved provider adapter and privacy contract.

Do not store:

- public URL;
- provider credentials;
- user-controlled filesystem path;
- raw file body;
- unrestricted original filename.

## 5. Domain ownership

`ProtectedObject` stores bytes metadata, but domain models own authorization.

Examples:

### PhotoAsset

PhotoAsset remains the photo business entity:

- Group;
- Child links;
- consent rules;
- uploaded_by;
- photo status.

It references one ProtectedObject for content.

Storage service does not decide whether a TEACHER/PARENT may see a photo.

### ContractVersion

ContractVersion references a ProtectedObject only when the approved contract document is available.

Contract role/Guardian entitlement remains Stage 7 logic.

### Receipt

Receipt references a ProtectedObject for fiscal/receipt content.

Receipt financial entitlement remains Stage 7 logic.

## 6. No generic reverse authorization

Do not authorize a user by querying:

`ProtectedObject.id == requested_id`

and then returning bytes.

Correct flow:

```text
request domain resource
→ domain service loads tenant-scoped Contract/Receipt/Photo
→ domain service proves actor entitlement
→ domain resource yields protected_object_id
→ storage service reads bytes
```

A ProtectedObject UUID alone does not establish access.

## 7. Object lifecycle

### pending_scan

Bytes/metadata have been accepted into a controlled temporary/quarantine path but are not downloadable.

### available

All required validation/scanning completed and the immutable object is approved for domain use.

### quarantined

Validation/scanning failed or content is suspicious.

No ordinary user content access.

### unavailable

Object metadata exists but backing storage/provider is not currently usable or the object cannot be served safely.

### removed

Object is no longer available to ordinary product flows under an approved lifecycle action.

Removal does not automatically mean physical destruction until the approved retention/destruction process completes.

## 8. Immutability

After status becomes `available`:

- object bytes cannot be overwritten in place;
- object key cannot be repointed to unrelated bytes;
- SHA-256 identifies the stored content;
- replacement creates a new ProtectedObject;
- domain record history points to the appropriate old/new objects.

This is mandatory for contracts and receipts and is also the default for photos.

## 9. Photo content

Initial photo content types:

- JPEG;
- PNG.

Photo pipeline:

1. domain authorization + consent checks;
2. size cap;
3. content decode;
4. reject malformed/unexpected image content;
5. re-encode to remove metadata/untrusted embedded chunks where the implementation supports it;
6. compute SHA-256 over final stored bytes;
7. store;
8. ProtectedObject available;
9. PhotoAsset references it.

No original EXIF/GPS metadata should be intentionally preserved.

## 10. Contract document content

Initial contract document type:

- PDF only.

Contract document pipeline requires:

1. DIRECTOR/domain authorization under Stage 7;
2. size cap;
3. MIME/content validation;
4. malware-scanning boundary;
5. immutable storage;
6. checksum;
7. version binding.

If production malware scanning is unavailable, production upload fails closed.

A contract document is not considered legally signed merely because it is stored.

## 11. Receipt document content

Initial receipt/fiscal content type:

- PDF only, unless a future provider contract explicitly requires another safe type.

Receipt content may be:

- imported from an approved fiscal/payment provider;
- registered by an authorized backend integration.

It is immutable and replacement creates a new Receipt/ProtectedObject relationship according to Stage 7 history rules.

## 12. Original filenames

Do not use original filename as:

- object key;
- authorization;
- log identifier;
- URL.

Prefer not to persist it at all.

For download, generate a safe domain filename such as:

- `contract-<safe-number>.pdf`;
- `receipt-<safe-id>.pdf`;
- `photo.jpg`.

The generated name is presentation only.

## 13. Storage key

The application generates an opaque internal key.

Requirements:

- not user-controlled;
- not derived from Child/Guardian names;
- does not contain passport/phone/email;
- unique;
- not exposed to ordinary clients.

A tenant prefix may be used internally for operational isolation, but authorization still depends on database/domain checks.

## 14. Hashing

Store SHA-256 of final stored bytes.

Uses:

- integrity verification;
- upload/storage troubleshooting;
- optional duplicate detection within an approved domain flow.

Hash is not a public identifier and is not a replacement for authorization.

Do not expose tenant-wide hash search.

## 15. Upload size

Each object kind has an explicit server-side size cap.

Exact values are frozen at implementation preflight based on existing photo constraints and provider limits.

The server must reject oversized content before unbounded memory/disk usage.

Client limits are UX only.

## 16. Validation

Do not trust:

- file extension;
- browser-provided MIME alone;
- original filename.

Validation uses actual bytes/content parser appropriate to the allowed kind.

Executable/script/archive formats are outside Stage 10 core.

## 17. Malware scanning boundary

General legal/fiscal documents require an approved scanning path before `available`.

The architecture supports a scanner adapter, but Issue #144 does not select a vendor.

Production behavior without approved scanning:

- contract/receipt upload requiring scan → fail closed;
- object cannot transition to available.

Synthetic dev/test behavior may use a deterministic fake scanner only in non-production environments.

## 18. Download model

Default Stage 10 core uses application-mediated authenticated streaming.

Advantages:

- entitlement is rechecked on every request;
- storage key remains private;
- no permanent bearer URL;
- simple revocation behavior.

The response uses privacy-safe headers, including:

`Cache-Control: private, no-store`

for sensitive content.

## 19. Signed URL boundary

Direct provider signed URLs are not part of Stage 10 core.

A later optimization may allow very short-lived signed delivery only after explicit security review of:

- expiry;
- revocation;
- referrer leakage;
- logs;
- browser caching;
- sharing;
- provider region.

No permanent/public URL is allowed.

## 20. Browser behavior

Frontend must not persist protected bytes or access metadata in:

- localStorage;
- sessionStorage;
- IndexedDB;
- service-worker offline cache.

Authenticated rendering/downloading is transient.

## 21. Local development storage

A local filesystem adapter may remain for:

- development;
- tests;
- preview with synthetic content.

Requirements:

- non-production only;
- private directory;
- generated keys;
- same metadata/API contract as production adapter;
- no real production files copied into it.

## 22. Production storage

Production protected-object writes remain disabled until Master Chat approves:

- storage provider;
- location/jurisdiction;
- encryption model;
- credentials/secret management;
- backup/replication behavior;
- retention/destruction;
- subprocessors;
- operational access.

Provider approval is a separate gate.

## 23. Provider adapter

The domain code depends on a narrow internal interface conceptually equivalent to:

- put immutable bytes;
- open/read bytes;
- stat/verify;
- remove according to approved lifecycle;
- health/readiness.

Provider-specific SDK types must not leak into domain schemas.

## 24. Failure handling

### DB commit fails after upload

The implementation must clean up the unreferenced object or record it for deterministic orphan cleanup.

### Storage write fails

No domain resource may claim content is available.

### Scan fails

Object becomes/remaims quarantined/unavailable; no ordinary download.

### Storage read fails

Return privacy-safe unavailable error; never return stale unrelated content.

## 25. Replacement

Replacement flow:

```text
authorize domain replacement
→ validate new content
→ create new ProtectedObject
→ make new object available
→ atomically point new domain version/reference
→ preserve old historical reference where domain requires it
```

Never overwrite old bytes in place.

## 26. Deletion and retention

Normal user-facing delete is not equivalent to physical deletion.

The system distinguishes:

- domain archive/removal;
- ProtectedObject removed/unavailable state;
- eventual physical purge under approved retention policy.

Issue #144 does not invent retention periods.

## 27. Product acceptance target

Future technical acceptance must prove:

```text
authorized Photo/Contract/Receipt domain request
→ protected content available
→ authenticated stream works
→ foreign tenant/role/participant denied
→ direct ProtectedObject UUID cannot bypass domain authorization
→ no public URL/object key exposed
→ replacement creates new immutable bytes
→ logs/Audit contain no file body
→ production without approved provider/scanner fails closed
```

Technical acceptance does not authorize real PII storage by itself.