# Stage 7 — Contracts, Billing and Receipts Data, Privacy and 152-FZ Boundary

**Status:** design proposal for Issue #137; frozen only after the design PR merges.
**Owner:** ONN9IX.
**Scope:** technical privacy/data design, not legal certification.
**Implementation:** NOT AUTHORIZED until Stage 6 integrated acceptance is complete.

## 1. Boundary

This document defines the technical privacy contract for Stage 7.

It does **not** establish that a real deployment complies with 152-FZ or other fiscal/payment requirements. Before processing real data, the operator must separately resolve legal basis, notices/consents where applicable, operator/processor roles, localization/hosting, retention, fiscalization/payment-provider obligations and organizational controls.

## 2. Data-minimization rule

Stage 7 stores only data required to:

- identify the Contract and its parties through existing entities;
- calculate Charges, Payments, Allocations and balances;
- preserve financial history;
- expose authenticated Contract/Receipt content when approved storage exists;
- reconcile provider/manual payment evidence;
- provide minimal notifications and Audit.

Do not add convenience PII that duplicates existing Guardian/Child data without a documented need.

## 3. Data classes

### Class A — ordinary business identifiers

Examples:

- UUIDs;
- Contract number;
- status enums;
- dates;
- amount_minor;
- currency;
- provider code;
- safe external references;
- receipt safe identifier.

These are still business data and remain tenant-scoped, but are not treated as unrestricted public information.

### Class B — personal data

Examples already present in Smart Garden:

- Guardian name;
- Child name;
- Guardian phone/email;
- Guardian↔Child relation.

Stage 7 references existing entities rather than copying these fields into every financial row.

### Class C — restricted identity data

Examples, only if a later legal/business gate proves necessity:

- passport/document series/number;
- issuing authority;
- issue date;
- identity-document scan;
- other government identity identifiers.

**Class C is not included in the Stage 7 core schema defined by Issue #137.**

### Class D — financial confidential data

Examples:

- payment references;
- allocation history;
- balance/debt/overpayment;
- refund/reversal data;
- fiscal receipt identifiers/content.

Access is role- and contract-entitlement-scoped.

### Class E — forbidden secrets

Smart Garden must never persist as Stage 7 business data:

- PAN/full card number;
- CVV/CVC;
- card PIN;
- bank login/password;
- acquiring secret/API key;
- provider signing secret;
- payment access token;
- session/cookie/token copied from auth;
- object-storage secret.

## 4. Core Stage 7 field review

### Contract

| Field | Purpose | Data class | Notes |
|---|---|---|---|
| id | internal identity | A | UUID |
| organization_id | tenant ownership | A | server-owned |
| child_id | contract subject relation | B reference | no copied Child profile |
| contracting_guardian_id | contract party relation | B reference | single contracting Guardian |
| contract_number | business identity | A | no PII encoding |
| status | lifecycle | A | enum |
| current_version_id | version link | A | server-owned |
| created_by | accountability | A/B reference | User UUID only |
| timestamps | lifecycle | A | timezone-aware |

### ContractVersion

| Field | Purpose | Data class | Notes |
|---|---|---|---|
| version_number | immutable sequence | A | integer |
| effective_from/to | legal/business period | A | date |
| billing_frequency | billing terms | A | enum |
| recurring_amount_minor | commercial term | D | integer minor units |
| currency | commercial term | A | RUB |
| due_rule | charge generation rule | A | structured |
| title | human presentation | A | no free-form identity data |
| acknowledgement refs/times | evidence | A/B reference | User UUID, timestamp |
| document_status | storage state | A | enum |
| document_object_id | protected object reference | D | opaque only |

### Charge

| Field | Purpose | Data class |
|---|---|---|
| contract/version references | financial relation | D |
| period/title/kind | obligation | A/D |
| amount_minor | obligation | D |
| issue/due dates | obligation | D |
| lifecycle | accountability | A |
| corrects_charge_id | history | D |

### Payment

| Field | Purpose | Data class | Rule |
|---|---|---|---|
| contract_id | entitlement/account | D | tenant-scoped |
| amount_minor/currency | received amount | D | required |
| source/status | state | D | enum |
| safe_external_reference | reconciliation | D | strict size/format |
| provider_code | adapter identity | A | no credential |
| external_event_id | idempotency | D | safe identifier only |
| timestamps | evidence | D | required |
| recorded_by | accountability | A/B ref | User UUID |

### Allocation / Adjustment / Receipt

Only identifiers, amounts, status, safe references, timestamps and protected object reference are allowed. No card credential, raw webhook, passport field or arbitrary evidence blob is added.

## 5. Contracting Guardian privacy rule

Financial information can reveal sensitive household/commercial information.

Therefore:

- an active ChildGuardian relation alone does not grant financial access;
- PARENT must also be the Contract's `contracting_guardian_id`;
- non-contracting Guardians do not see Contract number, balances, debt, Payments or Receipts;
- DIRECTOR/ADMIN access follows role scope;
- TEACHER has none.

This rule is evaluated server-side on every request.

## 6. Identity/passport data decision

Issue #137 freezes the following:

1. Raw passport/identity-document fields are **not** added to core Stage 7.
2. Contract metadata references the existing Guardian.
3. If a signed/scanned contract contains identity details, that content is treated as restricted binary content behind authenticated storage.
4. If structured passport fields later become mandatory, they require a separate serialized design and migration gate.

That future gate must specify exact fields, masking, encryption/key ownership, retention, export, backup treatment and read Audit.

## 7. Contract documents

Contract content may contain personal and legal data beyond metadata.

Rules:

- no public URL;
- no object key exposed as authorization;
- every content request re-checks session, tenant, role and Contract entitlement;
- content bytes are not copied into database logs, Audit.details, analytics or notifications;
- file name must not be trusted as an access-control decision;
- MIME/type and size are validated server-side;
- production upload/download fails closed without approved storage configuration;
- dev/test/preview use synthetic documents only.

## 8. Receipt documents

Receipt content receives the same protected-content rules.

Additionally:

- avoid exposing payer bank/card details if present in a provider artifact;
- prefer provider-generated/fiscal content without adding Smart Garden PII;
- replacement/correction receipt remains a separate historical object;
- old receipt content is not overwritten by a new one.

## 9. Browser storage

Do not store in `localStorage`, `sessionStorage` or long-lived IndexedDB:

- contract document bytes;
- receipt bytes;
- passport/identity values;
- payment references beyond transient UI need;
- balances/debt snapshots intended as authoritative;
- provider payloads;
- credentials/tokens.

HttpOnly session cookie remains authoritative.

Normal React/in-memory state for the active view is allowed.

## 10. URLs

Do not put in URL/query strings:

- passport/document values;
- Guardian name/phone/email;
- contract text;
- receipt content;
- payment secrets;
- provider credentials;
- raw external payload;
- full bank/card identifiers.

Allowed filters:

- UUID;
- enum status;
- date range;
- pagination;
- boolean overdue;
- safe business identifiers only where necessary and logging policy permits.

## 11. Technical logs

Allowed minimum:

- request_id;
- route/path template;
- method;
- status;
- duration;
- safe user_id/org_id if operationally necessary;
- stable safe error code.

Never log:

- full request bodies by default;
- passport/identity data;
- contract document body;
- receipt body;
- PAN/CVV;
- payment/provider token;
- provider signature secret;
- raw webhook body;
- bank credentials;
- temporary passwords;
- auth cookies/tokens;
- unnecessary Guardian/Child names/phones/emails.

Provider-event diagnostics should log safe event identifiers and result codes, not raw payloads.

## 12. Error handling

Client errors must be structured and privacy-safe.

Do not expose:

- stack trace;
- SQL;
- internal object-storage path;
- provider secret;
- webhook verification detail useful for bypass;
- another tenant's object existence;
- another Guardian's financial relationship.

Cross-tenant and non-entitled PARENT resource behavior follows the current hidden-resource contract.

## 13. Audit vs logs

Audit is a business accountability record. Technical logs are operational telemetry.

They must not be conflated.

Audit may include:

- action;
- actor UUID;
- organization UUID;
- target entity type/UUID;
- safe changed field names;
- financial amount/currency where accountability requires it;
- status transition;
- safe external event identifier.

Audit must not include:

- passport/document values;
- document bytes;
- receipt bytes;
- contract body;
- raw provider/webhook payload;
- PAN/CVV;
- bank credentials;
- storage credentials;
- unnecessary Guardian/Child contact data.

## 14. Restricted identity access Audit

If a later gate adds structured restricted identity data, every successful business read of unmasked sensitive values must be auditable.

The Audit entry records:

- actor;
- target Guardian/entity UUID;
- purpose/action enum;
- time.

It must not record the sensitive value itself.

ADMIN does not receive this access by default.

## 15. Financial integrity and privacy

Do not use mutable debt fields that operators can arbitrarily overwrite.

Privacy and accountability are improved when the balance is derived from explicit events:

- Charge;
- Payment;
- Allocation;
- Refund/Reversal;
- Correction.

The user-visible balance can be recalculated without retaining duplicate sensitive explanations.

## 16. Free-text minimization

Stage 7 should avoid arbitrary free-text fields in financial entities.

Where an operational note is truly necessary:

- separate it from provider/identity fields;
- set strict length;
- no passport/payment secrets;
- do not copy it to Audit/logs;
- define role visibility.

Core Issue #137 does not require a general financial-note field.

## 17. Manual payment evidence

A manual/offline Payment may require a safe business reference.

Allowed examples:

- internal receipt/reference number;
- bank transfer reference shortened/minimized where business needs justify it.

Not allowed:

- photo of a bank card;
- card number;
- login screenshot;
- arbitrary bank statement upload in core Stage 7.

If evidence-file upload is later needed, it requires the protected-document storage/privacy gate.

## 18. Provider boundary

Future provider integration must minimize data imported into Smart Garden.

Store only fields necessary to:

- verify event identity;
- map it to a Contract/Payment;
- know amount/currency/status/time;
- reconcile and support;
- reference fiscal Receipt.

Do not persist entire raw provider payload merely because it is available.

If temporary raw payload handling is necessary for signature validation, it is request-transient unless a separate retention/security decision explicitly approves encrypted evidence storage.

## 19. Webhook authenticity

Future integration must authenticate provider events through provider-supported cryptographic/signature mechanisms.

Requirements:

- secrets come from protected configuration;
- secrets are never database business fields;
- failed verification performs no financial mutation;
- replay is stopped by idempotency;
- event tenant mapping is server-controlled;
- signature/raw payload is not copied to Audit.

## 20. Data at rest

Core repository design does not choose a production hosting or encryption vendor.

Before real pilot, production design must establish:

- database encryption/storage protections;
- backup encryption/access;
- document object encryption;
- secret management;
- key ownership/rotation;
- hosting/jurisdiction;
- restore process without widening access.

For future structured Class C identity data, application-level/field-level protection must be explicitly evaluated rather than relying solely on generic database access control.

## 21. Data in transit

Production deployment requires authenticated HTTPS/TLS termination under the approved hosting design.

No contract/receipt/payment content over unauthenticated transport.

Provider callbacks require HTTPS and provider authenticity checks.

## 22. Retention

Issue #137 does not invent legal retention periods.

Before real pilot, retention/destruction decisions are required for:

- Contracts and versions;
- signed contract documents;
- Charges;
- Payments;
- Allocations;
- Adjustments/refunds/reversals;
- Receipts/fiscal documents;
- notifications;
- Audit;
- provider event identity records;
- backups.

`archived`, `cancelled`, `terminated`, `refunded` and `blocked` do not mean legal destruction.

## 23. Destruction

Financial/legal records must not be removed through normal UI hard-delete.

When a future approved retention policy requires destruction:

- it must be a privileged process;
- dependencies and legal holds must be considered;
- backup propagation must be defined;
- action must be auditable without retaining destroyed sensitive content;
- destruction must not corrupt financial ledger integrity.

## 24. Data export / subject requests

Before real pilot define how authorized requests are handled for:

- Guardian personal data;
- contract metadata;
- payment history;
- receipt data;
- protected documents.

Export must preserve other parties' privacy and must not include platform secrets or another Guardian's financial information.

Issue #137 does not implement a generic subject-access export endpoint.

## 25. Backups

Stage 5 backup/recovery gates remain mandatory.

Stage 7 additionally requires that future backups containing financial/document metadata:

- preserve tenant separation at restore/application layer;
- remain access-controlled;
- inherit approved retention;
- do not use real production copies for dev/test;
- protect provider/storage secrets separately from database backups.

## 26. Dev/test/preview

Use synthetic-only:

- Guardians;
- Children;
- Contract numbers;
- payment references;
- Charges/Payments;
- receipts;
- contract documents.

Do not use:

- real passports;
- real fiscal receipts;
- real bank transfer references;
- production provider events;
- real contracts;
- real parent names/phones/emails;
- production database dumps.

Synthetic demo documents should be visibly fictional.

## 27. Analytics

No third-party analytics/session replay may receive:

- Contract IDs correlated to PII;
- balances/debt;
- payment details;
- receipt identifiers/content;
- document content;
- passport data.

Product analytics, if introduced later, needs its own privacy review and data-minimized event schema.

## 28. AI

No Stage 7 Contract/Payment/Receipt PII is sent to external AI services.

Future AI use requires a separate explicit architecture/privacy decision and must not be silently introduced through logging, support tooling or document parsing.

## 29. Search indexing

Contract/document/receipt content must not be indexed by public search engines.

Internal full-text indexing of legal documents is not part of Stage 7 core.

If later required, it needs a privacy/security design including tenant isolation and deletion/retention semantics.

## 30. Notifications privacy

Notifications must use minimal wording.

Preferred:

- “Новое начисление доступно”
- “Оплата подтверждена”
- “Доступен чек”
- “Есть просроченное начисление”

Avoid placing in notification body:

- passport values;
- payment references;
- bank data;
- full contract text;
- receipt content.

Push/email/SMS delivery is not automatically approved; each external notification channel requires provider/data-flow review.

## 31. Dashboard privacy

Management financial dashboard may show aggregated amounts/counts.

Do not include:

- parent names in aggregate attention cards;
- document/passport data;
- receipt content;
- full payment reference.

Click-through to an authorized detailed screen is preferable to PII-heavy dashboard payloads.

## 32. Parent screen privacy

PARENT screens show only own eligible Contract account.

The UI must not leak:

- another Guardian's account;
- another Contract for the same Child;
- management reconciliation notes;
- provider secrets;
- internal Audit actor details unless intentionally part of support UX.

## 33. Teacher isolation

TEACHER must not receive Stage 7 data in:

- APIs;
- navigation;
- Today aggregator;
- Group detail;
- Child roster;
- direct/group communication payloads;
- notifications;
- browser-prefetched data.

A hidden frontend link alone is insufficient; Backend returns denial.

## 34. Required privacy negative tests

Future implementation must verify:

1. foreign tenant Contract UUID is hidden/denied;
2. non-contracting Guardian cannot read Contract;
3. inactive ChildGuardian relation revokes PARENT access;
4. TEACHER gets no Stage 7 data;
5. ADMIN cannot perform privileged contract-party changes;
6. ADMIN cannot read restricted identity data;
7. no client `organization_id` changes tenant;
8. no actor/guardian/payer spoofing;
9. contract/receipt content has no public URL;
10. content request rechecks entitlement;
11. PAN/CVV/payment secret fields are rejected/not modeled;
12. raw provider payload sentinel is absent from logs/Audit;
13. contract-document sentinel is absent from logs/Audit;
14. receipt-content sentinel is absent from logs/Audit;
15. passport sentinel cannot enter core schemas;
16. browser persistent storage contains no Stage 7 sensitive payload;
17. another PARENT cannot enumerate Receipt/Payment UUIDs;
18. duplicate provider event does not create duplicate financial data;
19. error responses reveal no cross-tenant existence;
20. synthetic-only fixtures are used.

## 35. Required financial-history tests

- issued Charge cannot be silently overwritten;
- confirmed Payment cannot be hard-deleted;
- correction links to original obligation;
- reversal/refund leaves history;
- replacement Receipt leaves previous Receipt;
- derived debt changes from explicit events;
- Audit details remain allowlisted.

## 36. Pre-pilot unresolved decisions

Before real data/pilot, Master Chat must have approved external/legal inputs for at least:

- organization as personal-data operator/controller;
- processors/subprocessors;
- legal basis for Guardian/Child/contract data;
- whether structured passport data is actually required;
- whether/how electronic acknowledgement/signature has legal effect;
- payment/acquiring provider and data flow;
- fiscalization/receipt obligations and provider;
- hosting/data location/localization;
- production document/receipt storage;
- secret/key management;
- retention/destruction periods;
- subject requests/export;
- incident/breach process;
- backup location/protection/retention;
- notification providers;
- provider contracts and cross-border data flow if any;
- Roskomnadzor notification/registration obligations where applicable.

## 37. Acceptance boundary

A green Stage 7 technical acceptance proves only that the implemented software matches this frozen technical contract and tests.

It does not by itself prove:

- 152-FZ compliance;
- fiscal-law compliance;
- payment-services compliance;
- enforceability of contract acknowledgement;
- authorization to process real passport/payment data;
- authorization to start a real kindergarten pilot.