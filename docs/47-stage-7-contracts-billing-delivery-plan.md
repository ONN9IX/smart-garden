# Stage 7 — Contracts, Billing and Receipts Delivery Plan

**Status:** design proposal for Issue #137; frozen only after the design PR merges.
**Owner:** ONN9IX.
**Design baseline:** `193cb160636b52a318a4eccc05496236ee402572`.
**Implementation prerequisite:** Stage 6 integrated acceptance must be complete and frozen.

## 1. Required order

```text
Stage 6 complete TEACHER delivery
→ Stage 6 integrated acceptance
→ Stage 6 FROZEN
→ Stage 7 design #137 merge/freeze
→ Stage 7 implementation preflight
→ S7-FINANCIAL-FOUNDATION
→ merge + post-merge CI green
→ S7-CONTRACTS-BILLING-CABINET
→ merge + post-merge CI green
→ optional provider/storage integrations in separate gates
→ S7-ACCEPTANCE
```

Issue #137 is docs-only and may be designed while #131 is active. No Stage 7 runtime implementation begins before Stage 6 acceptance.

## 2. Design gate

Issue #137 owns exactly:

- `docs/44-stage-7-contracts-billing-product-spec.md`
- `docs/45-stage-7-contracts-billing-permissions-and-api.md`
- `docs/46-stage-7-contracts-billing-data-privacy.md`
- `docs/47-stage-7-contracts-billing-delivery-plan.md`

No code, migrations, tests, CI, dependencies or shared coordination files.

After the PR merges, this package becomes the frozen Stage 7 Contracts/Billing design baseline.

## 3. Stage 6 prerequisite

Before any Stage 7 implementation Issue is created:

1. Issue #131 complete TEACHER cabinet is merged;
2. post-merge CI is green;
3. Stage 6 integrated acceptance verifies all four roles;
4. Stage 6 is explicitly frozen;
5. `main` exact SHA is recorded;
6. `docs/CURRENT_STATE.md`/coordination state is updated by the serialized Stage 6 acceptance flow.

Stage 7 must start from that fresh exact baseline, not from the design branch baseline.

## 4. Stage 7 implementation preflight

Master Chat inspects only the post-Stage-6 source-of-truth and verifies:

- current migration head;
- current router extension points;
- current model registry;
- current Audit action allowlist mechanism;
- Notification extension mechanism;
- current management/PARENT navigation extension points;
- no active branch overlaps proposed Stage 7 write-sets;
- no auth/RBAC redesign is required;
- protected document storage remains unavailable unless separately approved.

If a shared extension point must change, that work belongs in the serialized Foundation Issue, not an ad-hoc parallel patch.

## 5. S7-FINANCIAL-FOUNDATION — serialized

**Owner:** ONN9IX unless Master Chat explicitly assigns otherwise.
**PARALLEL-SAFE:** NO.

Purpose: create the shared Stage 7 financial data foundation exactly once.

Expected scope:

### Backend

- Contract model;
- ContractVersion model;
- Charge model;
- Payment model;
- PaymentAllocation model;
- PaymentAdjustment model;
- Receipt model;
- idempotency persistence/constraints if needed;
- one Stage 7 Alembic migration/head;
- model registry;
- core money/status enums;
- reusable financial authorization primitives;
- Contracting-Guardian entitlement helper;
- privacy-safe Audit action allowlist additions;
- minimal Notification kinds/event hooks if shared files require them;
- router aggregation extension point for isolated Stage 7 namespaces;
- synthetic seed/fixture support only if necessary.

### Frontend shared work

Only shared role-aware navigation/route extension points proven necessary by preflight.

Do not redesign auth/AppShell architecture.

### Foundation tests

At minimum:

- migration upgrade on PostgreSQL;
- model constraints;
- same-tenant Child/Guardian/Contract relation;
- contracting Guardian eligibility;
- RUB/integer-money constraints;
- unique Contract number scope;
- idempotency uniqueness;
- no passport/card-secret schema fields;
- TEACHER permission denial primitives.

## 6. Foundation migration rule

Prefer exactly one Stage 7 schema migration for the frozen core data model.

No parallel migration heads.

If implementation discovers a material schema contradiction, STOP and return to Master Chat rather than adding an unreviewed second migration.

After Foundation merges:

- require post-merge CI green;
- record fresh `main` SHA;
- rebaseline the cabinet Issue.

## 7. Primary implementation — S7-CONTRACTS-BILLING-CABINET

After Foundation, create one large self-contained Issue:

`S7-CONTRACTS-BILLING-CABINET — management + parent financial workflow`

Preferred delivery:

- one major Issue;
- one fresh branch;
- one PR;
- many internal commits/milestones;
- ordinary defects fixed in the same branch.

The Issue should own isolated Stage 7 backend/frontend namespaces and explicit tests.

## 8. Cabinet product scope

Implement the complete provider-neutral product workflow:

1. Contract list/detail.
2. Contract draft/party selection.
3. Contract versions/amendments.
4. submit/acknowledge/activate/terminate/cancel.
5. Charge draft/issue/correct/cancel.
6. Payment manual/provider-neutral metadata model operations.
7. Allocation/reconciliation.
8. debt/overdue/credit calculations.
9. reversal/refund semantics.
10. Receipt metadata.
11. fail-closed contract/receipt content boundary.
12. DIRECTOR screens.
13. ADMIN operational screens.
14. PARENT contracts/balance/charges/payments/receipts.
15. Stage 7 notifications.
16. Stage 7 Audit.
17. responsive/mobile UX.
18. mandatory negative/security/privacy/financial-integrity tests.
19. browser E2E and regression.

Do not split these into many Master Chat checkpoints unless a STOP condition occurs.

## 9. Recommended internal implementation order

Internal milestones only:

1. Stage 7 schemas/services/router structure.
2. Contract read/write lifecycle.
3. Contract version/acknowledgement.
4. Charge lifecycle.
5. Payment recording/state.
6. allocation and derived balance.
7. refund/reversal/correction.
8. Receipt metadata.
9. management API completion.
10. PARENT eligibility/read APIs.
11. Notifications/Audit.
12. DIRECTOR/ADMIN UI.
13. PARENT UI.
14. protected-content fail-closed UI states.
15. mobile/responsive pass.
16. backend negative tests.
17. financial concurrency/idempotency tests.
18. browser E2E.
19. frozen Stage 1–6 regression.
20. full required CI.

## 10. Suggested isolated namespaces after Foundation

Exact paths are established by the future Issue after inspecting post-Stage-6 repository structure.

Preferred shape if compatible:

### Backend

- `backend/app/api/billing/**`
- `backend/app/api/contracts/**`
- `backend/app/schemas/billing/**`
- `backend/app/schemas/contracts/**`
- `backend/app/services/billing/**`
- `backend/app/services/contracts/**`
- Stage 7-specific tests

PARENT adapters may live in the current PARENT namespace only with an exact write-set and no collision with Stage 6 TEACHER-owned parent surfaces.

### Frontend

- `frontend/src/app/contracts/**`
- `frontend/src/app/billing/**`
- `frontend/src/features/contracts/**`
- `frontend/src/features/billing/**`
- `frontend/src/lib/api/contracts/**`
- `frontend/src/lib/api/billing/**`
- Stage 7-specific types/tests

PARENT Stage 7 pages must use a clearly owned non-overlapping namespace decided after Stage 6 merge.

Do not create a second shared API client/auth system.

## 11. DIRECTOR delivery

Required DIRECTOR functionality:

- list/create Contracts;
- choose Child + contracting Guardian;
- edit draft;
- submit for acknowledgement;
- activate;
- create amendment;
- terminate/cancel;
- read versions;
- issue/correct/cancel Charges;
- record/read Payments;
- allocate/reconcile;
- reverse/refund;
- read debt/overpayment;
- register/read Receipts;
- authenticated document actions when configured;
- Audit visibility.

No raw passport UI in core Stage 7.

## 12. ADMIN delivery

Required ADMIN functionality:

- operational Contract list/detail subset;
- Charges;
- Payments;
- Reconciliation;
- debt/overpayment;
- read reversal/refund results; manual reversal/refund actions remain DIRECTOR-only;
- Receipt metadata/content where operationally justified.

Must not expose:

- contract party mutation;
- activation/termination/cancellation controls;
- restricted identity;
- Stage 7 Audit;
- provider/storage secrets.

## 13. PARENT delivery

Required PARENT functionality:

- My contracts;
- current version;
- acknowledgement;
- current balance;
- outstanding/overdue Charges;
- payment history/status;
- overpayment/credit;
- Receipts;
- authenticated content when available;
- clear fail-closed/unavailable state when production binary storage is not configured.

Non-contracting Guardian denial is mandatory.

## 14. TEACHER regression

No TEACHER Stage 7 product work.

Regression must verify:

- no Stage 7 nav;
- no Stage 7 Today payload;
- no debt/payment signal in Group/Child views;
- direct Stage 7 API access denied.

## 15. Document/receipt storage boundary

The provider-neutral cabinet may implement:

- metadata;
- protected object reference interface;
- authenticated content endpoint contract;
- fail-closed behavior.

It must not select/connect a production external storage vendor during the core cabinet Issue unless a separate explicit infrastructure/privacy gate has already frozen that choice.

### Separate future Issue

If production file storage is approved:

`S7-PROTECTED-DOCUMENT-STORAGE`

Serialized if it touches shared infrastructure/configuration.

It must define:

- storage provider/location;
- object key design;
- encryption;
- auth-mediated content access;
- upload validation;
- malware/content scanning decision;
- retention;
- backup;
- deletion;
- secrets;
- tenant boundary.

## 16. Payment/acquiring integration boundary

Core Stage 7 does not execute real payments.

A future provider Issue is separate:

`S7-PAYMENT-PROVIDER-INTEGRATION`

Prerequisites:

- provider selected by explicit Chat decision;
- legal/privacy/data-flow review;
- credential/secret design;
- webhook verification design;
- production endpoint/network design;
- idempotency mapping;
- sandbox test capability;
- fiscalization relationship resolved.

Do not put production credentials in GitHub, seed, tests or screenshots.

## 17. Fiscal/receipt integration boundary

If the selected payment provider does not fully cover fiscal receipts, create a separate:

`S7-FISCAL-RECEIPT-INTEGRATION`

Only after legal/business responsibility and provider are explicit.

Core Receipt model remains provider-neutral.

## 18. Structured identity/passport boundary

If a real Contract legally requires structured passport fields beyond protected document content, create a separate serialized gate:

`S7-RESTRICTED-IDENTITY-DATA`

This gate requires legal/privacy approval before migration.

It must not be silently bundled into the cabinet implementation.

## 19. Audit integration

If the current Audit writer needs shared allowlist changes, Foundation owns them.

Cabinet code must call the frozen Audit interface and never invent arbitrary details.

Required business actions are listed in docs/45.

DIRECTOR remains the only ordinary Audit reader under the current architecture.

## 20. Notification integration

Prefer reusing existing Notification.

If shared Notification model changes are needed, Foundation serializes them.

Stage 7 cabinet owns only domain event generation and PARENT/management presentation within its exact write-set.

## 21. Money implementation rules

Future implementation must use:

- integer minor units;
- RUB in Stage 7 core;
- no JS floating-point arithmetic as financial source of truth;
- backend calculations/validation;
- explicit transaction boundaries;
- database constraints where practical;
- deterministic derived balance.

Frontend formatting is presentation only.

## 22. Concurrency tests

At minimum cover:

- two attempts to confirm same external event;
- two concurrent allocations against same Payment;
- allocation and refund collision;
- duplicate Contract acknowledgement;
- duplicate Charge issue/correction command where idempotency applies.

No scenario may create duplicated money effects.

## 23. Required backend negative tests

Tenant:

- foreign Contract;
- foreign Charge;
- foreign Payment;
- foreign Receipt;
- foreign Child/Guardian party selection.

Role:

- TEACHER all denied;
- PARENT management writes denied;
- ADMIN privileged Contract lifecycle denied;
- ADMIN Audit denied.

Parent:

- non-contracting Guardian denied;
- inactive ChildGuardian denied;
- forged guardian/user/org fields ignored/rejected;
- UUID enumeration denied.

Money:

- negative/zero invalid amount where business rule forbids it;
- non-RUB rejected;
- over-allocation rejected;
- over-refund rejected;
- pending/failed Payment not counted;
- issued history immutable;
- duplicate external event idempotent;
- corrected/reversed/refunded history preserved.

Privacy:

- passport fields absent/rejected;
- card-secret fields absent/rejected;
- protected content no public URL;
- sensitive sentinels absent from logs/Audit.

## 24. Required DIRECTOR browser flow

```text
login
→ Contracts
→ create draft
→ choose Child + contracting Guardian
→ submit for acknowledgement
→ activate
→ create/issue Charge
→ Payments
→ record/observe confirmed Payment
→ allocate
→ verify balance/debt
→ Receipts
→ Audit
→ logout
```

Also cover amendment/termination and refund/reversal at least in targeted E2E or integration tests.

## 25. Required ADMIN browser flow

```text
login
→ Contracts operational view
→ Charges
→ Payments
→ Reconciliation
→ Debt
→ Receipts
→ privileged contract controls absent
→ Audit absent/403
→ logout
```

## 26. Required PARENT browser flow

```text
login
→ My contracts
→ review/acknowledge eligible version
→ Balance
→ Charges
→ Payments
→ Receipts
→ content unavailable or authenticated content depending on config
→ logout
```

Separate negative browser/API coverage verifies a non-contracting Guardian cannot see the same Child's Contract.

## 27. Regression

Keep green:

- Stage 1 auth/session;
- Stage 2 Groups/Children/Guardians/PARENT;
- Stage 3 Employees/ADMIN account/Attendance;
- Stage 4 Audit/Announcements/Dashboard;
- Stage 5 security/CI/backup-recovery;
- Stage 6 all four-role acceptance;
- TEACHER assignment/participant/privacy rules;
- parent communication/diary/poll/photo flows.

Stage 7 may not weaken old tests.

## 28. Validation during implementation

Use targeted checks while coding.

Before PR handoff:

Backend:

- `ruff check .`;
- all Stage 7 backend tests;
- relevant frozen regression;
- migration/PostgreSQL checks.

Frontend:

- `npm run lint`;
- `npm run build`;
- Stage 7 browser specs;
- relevant Stage 6 browser regression.

Also:

- `git diff --check`;
- exact write-set review;
- no secret/real PII fixtures;
- full required repository CI.

## 29. STOP conditions

Return to Master Chat before continuing if work requires:

- changing frozen auth/session architecture;
- changing tenant derivation;
- weakening RBAC;
- exposing TEACHER financial data;
- changing the single-contracting-Guardian decision;
- adding another currency;
- adding structured passport fields;
- storing card/payment secrets;
- introducing external production storage/provider;
- choosing payment/fiscal/e-sign vendor;
- new unscheduled migration head;
- weakening immutable financial history;
- modifying Stage 1–6 semantics beyond approved additive integration;
- unresolved legal/retention/hosting decision needed for implementation;
- real PII in dev/test/preview.

## 30. Ordinary defect rule

Fix in the same implementation branch:

- validation bug;
- balance calculation bug consistent with frozen rules;
- missing filter;
- responsive UI;
- serialization issue;
- local RBAC defect;
- missing test;
- CI defect caused by the current change.

Create a separate corrective Issue only for independent architecture, auth, tenant, security, privacy, migration or frozen-contract findings.

## 31. PR and merge discipline

For every major delivery:

```text
one Issue
→ one fresh branch
→ implementation
→ targeted tests
→ PR
→ CI
→ Master Chat review
→ explicit merge decision
→ post-merge CI
```

No developer self-merge.

## 32. S7-ACCEPTANCE

Serialized final technical acceptance after all required core delivery merges.

Acceptance verifies:

- DIRECTOR end-to-end Contract→Charge→Payment→Receipt workflow;
- ADMIN operational permissions and denials;
- PARENT contracting-Guardian entitlement;
- TEACHER isolation;
- tenant isolation;
- immutable financial history;
- debt/overpayment calculations;
- idempotency/concurrency;
- protected document/receipt boundary;
- privacy-safe Audit/logging;
- no real PII/dev data;
- preserved Stage 1–6 regression;
- all required CI/security/backup gates.

If production provider/storage integrations are intentionally deferred, acceptance records them as future/pre-pilot prerequisites rather than pretending they are implemented.

## 33. Acceptance does not authorize production

Even after Stage 7 technical acceptance, real-pilot approval still requires separate resolution of:

- 152-FZ/legal basis and organizational controls;
- hosting/data location;
- retention/destruction;
- production document storage;
- acquiring/payment provider;
- fiscalization;
- e-signature/legal acknowledgement if needed;
- restricted identity data if needed;
- secrets/keys;
- operational incident process.

## 34. Desired final Stage 7 state

The provider-neutral core should be usable with synthetic data as a complete demonstrable product:

```text
DIRECTOR manages contract and billing
ADMIN operates daily reconciliation
PARENT sees only their own financial relationship
TEACHER sees none of it
financial history is deterministic and auditable
real payment/storage providers remain explicit controlled integrations
```

This maximizes product completeness without prematurely coupling Smart Garden to a vendor or expanding its PII risk.