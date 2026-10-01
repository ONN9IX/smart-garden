# Stage 10 — Protected Storage Delivery Plan

**Status:** design proposal for Issue #144; frozen only after the design PR merges.
**Owner:** ONN9IX.
**Design baseline:** `4993d3e1f3128b8a1f23c7d7c085084b062fc6b8`.

## 1. Strategic sequencing decision

Stage 10 protected-storage foundation should be implemented **before Stage 7 Financial Foundation** if Stage 7 schema is going to persist ContractVersion/Receipt protected-object references.

Reason:

- Stage 7 already freezes document_object_id semantics;
- implementing storage first avoids temporary untyped UUID references;
- Photos can move off the local-only production-fail-closed boundary at the same time;
- one shared migration/adapter contract is cleaner than three domain-specific storage implementations.

Preferred post-Stage-6 sequence:

```text
Stage 6 integrated acceptance
→ Stage 6 FROZEN
→ Stage 10 storage preflight
→ S10-PROTECTED-STORAGE-FOUNDATION
→ merge + post-merge CI
→ Stage 7 Financial Foundation
→ Stage 7 Contracts/Billing
→ Stage 8 Parent consolidation
```

Stage 9 kiosk may run separately when shared-file ownership is proven disjoint.

## 2. Design gate

Issue #144 owns exactly:

- `docs/56-stage-10-protected-storage-product-spec.md`
- `docs/57-stage-10-protected-storage-api-security.md`
- `docs/58-stage-10-protected-storage-data-privacy.md`
- `docs/59-stage-10-protected-storage-delivery-plan.md`

No runtime code, migration, dependency, CI or shared coordination edits.

## 3. Runtime prerequisite

No Stage 10 implementation before:

1. Issue #131 merged;
2. Stage 6 post-merge CI green;
3. Stage 6 integrated acceptance/freeze;
4. fresh current main SHA recorded;
5. PhotoAsset/current storage implementation re-inspected;
6. current migration head recorded;
7. Stage 7 runtime has not independently created a conflicting document-storage model.

## 4. Preflight

Read only:

- current Protected/Photo-related models/services;
- frozen Stage 6 photo contract;
- Stage 7 ContractVersion/Receipt design;
- current model registry/migration head;
- backend router/service extension points;
- config/environment pattern;
- Stage 5 backup/recovery/security;
- relevant tests.

Preflight determines the exact migration and legacy PhotoAsset transition.

## 5. S10-PROTECTED-STORAGE-FOUNDATION

Create one serialized major Issue.

**PARALLEL-SAFE:** NO while it owns migration/model registry/shared storage configuration.

Expected scope:

### Database

- ProtectedObject model/table;
- one migration;
- tenant/index/unique constraints;
- lifecycle fields;
- PhotoAsset protected-object reference;
- deterministic legacy synthetic-photo compatibility/backfill strategy if required.

### Backend infrastructure

- storage adapter interface;
- local non-production adapter;
- production disabled/fail-closed adapter;
- validation/sanitization pipeline;
- scanner adapter interface;
- deterministic non-production fake scanner where necessary for tests only;
- protected-object service;
- cleanup/orphan handling;
- content streaming primitive.

### Photo integration

- Stage 6 PhotoAsset writes ProtectedObject;
- existing consent/assignment/participant authorization remains domain-owned;
- production still fails closed unless real provider/scanner has separately been approved.

### Tests

- migration;
- metadata constraints;
- tenant isolation;
- environment isolation;
- immutable content;
- local adapter;
- disabled production behavior;
- photo integration/regression;
- privacy/logging sentinels.

## 6. One migration rule

Prefer one Stage 10 schema migration.

No parallel migration heads.

If Stage 7 Foundation has already begun and owns the migration lane, STOP and re-sequence rather than creating competing heads.

## 7. Legacy PhotoAsset transition

Exact current PhotoAsset schema at implementation time is authoritative.

Target state:

- PhotoAsset stores domain metadata;
- protected bytes metadata live in ProtectedObject;
- PhotoAsset references ProtectedObject;
- domain consent rules remain unchanged.

Do not perform a destructive migration that assumes existing production files are disposable.

Because real production PII is not yet authorized, synthetic dev/preview fixture reset may be used where appropriate, but migration code must still be deterministic and safe.

## 8. Provider-independent Foundation

The Foundation must not select a production cloud/object vendor.

Production backend remains disabled until a later provider Issue.

This allows:

- schema/domain integration;
- local synthetic development;
- full authorization testing;
- future provider swap through one adapter.

## 9. Stage 7 dependency after Foundation

After Stage 10 Foundation merges, Stage 7 Financial Foundation may create:

- ContractVersion protected object FK/reference;
- Receipt protected object FK/reference;

against the now-real ProtectedObject model.

Stage 7 does not create another storage table/adapter.

## 10. Stage 7 document integration

Within Stage 7 Contracts/Billing cabinet:

### Contract

DIRECTOR upload/attach flow uses Stage 10 storage service after Stage 7 domain authorization.

PARENT read uses Stage 7 contracting-Guardian entitlement first, then Stage 10 content service.

### Receipt

Receipt provider/management registration attaches an approved protected object.

PARENT receipt access revalidates Stage 7 financial entitlement.

No generic storage authorization.

## 11. Production provider integration Issue

Separate future serialized Issue:

`S10-PROTECTED-STORAGE-PROVIDER`

Prerequisites:

- selected provider;
- approved region/localization;
- security/privacy review;
- credential/secret plan;
- encryption/KMS decision;
- backup/replication decision;
- operational access;
- cost/limits;
- sandbox/test environment.

This Issue implements only the adapter/config needed for the approved provider.

## 12. Malware scanner integration Issue

If the chosen production storage/provider does not include an approved scanning workflow, create:

`S10-MALWARE-SCANNER-INTEGRATION`

Prerequisites:

- approved scanner/provider/data flow;
- region/subprocessor review;
- failure/quarantine behavior;
- privacy/logging contract.

General PDF uploads remain fail-closed until scan capability is approved.

## 13. Exact provider decision is deferred

Do not choose in the design/foundation:

- S3-compatible vendor;
- Yandex/AWS/other cloud;
- antivirus vendor;
- CDN;
- signed-URL model.

The production choice should be made using actual deployment/legal/cost requirements closer to pilot.

## 14. Shared-file coordination

Likely serialized shared areas:

- model registry;
- migration head;
- backend settings/config;
- dependency file if provider/validation library is required;
- backend router only if shared registration lacks extension point.

Keep the main product implementation inside isolated storage/domain namespaces where possible.

Any new dependency must be justified and security-audited.

## 15. Photo content validation

During Foundation, preserve current Stage 6 photo constraints and add:

- actual image decoding;
- metadata stripping/re-encode;
- max byte size;
- max dimensions/pixels;
- checksum;
- immutable write.

No biometrics or image analysis.

## 16. PDF pipeline in Foundation

Foundation can freeze/test the abstract PDF validator/scanner pipeline without enabling production PDFs.

Non-production synthetic test PDF may pass a deterministic fake clean scanner.

Production scanner unavailable → fail closed.

## 17. Content streaming

Implement one internal streaming primitive but keep routes domain-specific.

Requirements:

- domain authorization already passed;
- same-tenant ProtectedObject;
- available state;
- expected kind;
- backend read;
- safe response headers;
- no object key exposure.

## 18. Orphan cleanup

Because storage and DB are separate systems, implementation must include deterministic cleanup.

Allowed design:

- temporary upload with promotion; or
- orphan record/job with bounded cleanup.

The chosen solution must be testable and environment/tenant safe.

Do not create an unbounded best-effort filesystem leak.

## 19. Object removal

Foundation may implement internal remove/purge primitives, but ordinary domain UIs do not get a generic delete.

Physical purge remains disabled until retention rules are approved.

Synthetic test cleanup is separate from production retention.

## 20. Required backend tests

### ProtectedObject model

- same-tenant ownership;
- kind/status validation;
- positive size;
- hash format;
- unique backend/key;
- unavailable/quarantine cannot stream.

### Local adapter

- immutable write/read;
- missing object;
- environment private directory;
- generated key;
- no public URL.

### Production disabled

- write fails closed;
- read fails closed;
- no local fallback.

### Authorization

- no generic content route;
- photo consent/assignment regression;
- cross-tenant denial;
- wrong role denial.

### Privacy

- object key absent from API;
- file body absent from Audit/logs;
- metadata sanitizer;
- synthetic fixtures.

### Failure

- DB rollback/orphan;
- storage failure;
- scanner fail/infected;
- hash/integrity mismatch.

## 21. Required browser/integration tests

Photo:

```text
TEACHER upload synthetic image
→ available protected object
→ TEACHER authorized render
→ eligible PARENT render
→ consent withdrawal
→ both domain rules re-evaluated
```

Contract/Receipt browser tests belong to Stage 7 after those domains exist.

## 22. Stage 5 backup/recovery integration

Stage 10 acceptance must document that PostgreSQL backup does not by itself protect binary objects.

Before real production provider enablement, provider backup/replication/restore must be tested separately.

Do not weaken existing PostgreSQL recovery gates.

## 23. Environment safety

Required tests/config assertions:

- test/dev backend cannot target production credentials;
- production cannot use local dev adapter;
- preview cannot access production storage;
- destructive test cleanup refuses production environment.

## 24. Parallelism after Foundation

Once S10-PROTECTED-STORAGE-FOUNDATION is merged and green:

- Stage 9 kiosk may proceed if write-sets are disjoint;
- Stage 7 Foundation may proceed using ProtectedObject;
- later Stage 10 provider integration remains serialized if it changes shared config/dependencies.

Master Chat must explicitly mark parallel Issues safe.

## 25. STOP conditions

Return to Master Chat if implementation requires:

- a second storage metadata model;
- generic public upload/download;
- public bucket/object;
- production provider selection not yet approved;
- real PII files in dev/test;
- OCR/AI/face recognition;
- unapproved new file type;
- unapproved scanner data flow;
- signed URL introduction;
- retention period invention;
- cross-environment storage access;
- new migration conflict;
- auth/RBAC/tenant weakening.

## 26. Ordinary defect rule

Fix in the same Foundation branch:

- validation bug;
- MIME detection bug;
- sanitizer issue;
- local adapter bug;
- object cleanup bug;
- response-header bug;
- missing negative test;
- CI failure caused by current diff.

Independent provider/legal/privacy architecture findings return to Master Chat.

## 27. Validation before PR

Backend:

- ruff;
- storage/model targeted pytest;
- Stage 6 photo regression;
- PostgreSQL migration round trip.

Frontend if affected:

- lint;
- build;
- targeted photo browser spec.

Also:

- dependency audit;
- git diff --check;
- exact write-set;
- secret scan/current CI;
- full required repository CI.

## 28. S10-ACCEPTANCE

After Foundation merge:

- post-merge CI green;
- migration head singular;
- Photo flow uses ProtectedObject;
- production storage remains fail-closed without provider;
- environment isolation verified;
- no public URL;
- no PII leakage;
- old Stage 1–6 regressions green.

This acceptance freezes the provider-independent storage foundation.

## 29. Real-production storage readiness

A real-pilot storage readiness decision occurs only after:

1. Provider integration merged.
2. Scanner integration available where required.
3. Data location/legal review complete.
4. Encryption/key strategy approved.
5. Backup/restore tested.
6. Retention/destruction approved.
7. Operational access and incident process approved.

## 30. Desired result

The final architecture is:

```text
Photos ───────────┐
Contracts ────────┼→ domain authorization → ProtectedObject → storage adapter
Receipts ─────────┘                                  │
                                                    ├→ local synthetic dev
                                                    └→ approved production provider later
```

One private storage boundary, multiple domain policies, no public-file shortcut.