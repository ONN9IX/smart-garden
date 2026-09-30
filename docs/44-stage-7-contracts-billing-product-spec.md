# Stage 7 — Contracts, Billing and Receipts Product Specification

**Status:** design proposal for Issue #137; frozen only after the design PR merges.
**Owner:** ONN9IX.
**Scope:** future Stage 7 product design only.
**Implementation:** NOT AUTHORIZED until Stage 6 integrated acceptance is complete.
**Baseline:** `193cb160636b52a318a4eccc05496236ee402572`.

## 1. Goal

Add one coherent financial/document workflow to Smart Garden:

```text
Contract
→ Charge
→ Payment
→ Allocation
→ Receipt
→ Parent-visible history
```

The product must let the kindergarten manage the commercial relationship with a parent without turning Smart Garden into a bank, accounting ERP or legal-signature provider.

Stage 7 is tenant-scoped and reuses the existing User, Guardian, Child, ChildGuardian, Organization, Notification and Audit concepts. It does not change Stage 1–6 auth/session semantics.

## 2. Product principles

1. Backend authorization is authoritative.
2. Tenant is derived only from authenticated User.
3. Money is represented in integer minor units, never binary floating point.
4. Stage 7 MVP currency is `RUB` only.
5. Financial history is append-oriented. Confirmed financial events are not silently deleted.
6. Contract, payment and receipt content is never exposed by a public URL.
7. Card credentials and banking secrets are never stored by Smart Garden.
8. TEACHER has no Contracts/Billing/Receipts access.
9. PARENT access is narrower than ordinary child visibility: financial access is tied to the contracting guardian.
10. Technical acceptance is not legal certification or authorization to process real production PII.

## 3. Roles

### DIRECTOR

DIRECTOR is the privileged business owner inside one Organization.

DIRECTOR may:

- create and manage contract metadata;
- select the contracting Guardian and Child;
- activate, terminate or cancel a contract;
- create amendments;
- issue/correct/cancel charges;
- view and reconcile payments;
- record approved manual/offline payment evidence metadata;
- register payment reversals/refunds;
- register receipt metadata;
- view authenticated contract/receipt content when the storage boundary is enabled;
- view debt/overpayment and reconciliation;
- access privacy-safe Audit;
- perform restricted identity/document access only if a later legal/privacy gate authorizes that data class.

DIRECTOR may not:

- choose another tenant;
- store card PAN/CVV or banking passwords;
- bypass immutable financial history;
- claim Smart Garden acknowledgement is a qualified electronic signature.

### ADMIN

ADMIN is an operational billing role, not the owner of legal identity data.

ADMIN may:

- list contract operational metadata needed to bill;
- create/issue/correct/cancel charges;
- list payments;
- record approved manual/offline payment metadata;
- reconcile payments and allocations;
- view debt/overpayment;
- register/read receipt metadata;
- use normal authenticated receipt content only when explicitly allowed by the storage contract.

ADMIN may not:

- change the contracting party;
- activate/terminate/cancel the legal contract;
- read restricted identity/passport data;
- read privileged Audit;
- change Organization-wide financial/provider configuration;
- access another tenant.

### TEACHER

TEACHER has no Stage 7 access:

- no contracts;
- no charges;
- no balances/debt;
- no payments;
- no receipts;
- no identity documents.

No Stage 7 amount or debt indicator is added to the TEACHER cabinet.

### PARENT

PARENT may read only Stage 7 resources for which all eligibility conditions are true:

1. the User resolves to the Guardian under current auth rules;
2. that Guardian is the contract's `contracting_guardian_id`;
3. the Guardian has an active ChildGuardian relationship to the contract Child;
4. the Contract belongs to the authenticated User's Organization;
5. the resource belongs to that Contract/account.

A non-contracting Guardian does not automatically receive contract, debt, payment or receipt visibility merely because they are linked to the same Child.

## 4. Contract party decision

Stage 7 freezes **one contracting Guardian per Contract**.

A Contract links:

- one Organization;
- one Child;
- one `contracting_guardian_id`;
- one immutable Contract identity/number;
- one current Contract version.

Other Guardians linked to the Child remain outside the financial contract unless a future explicit authorization/co-contracting design gate adds that capability.

This avoids accidental disclosure of one Guardian's financial relationship to another Guardian.

## 5. Contract lifecycle

Contract states:

- `draft` — management preparation; not visible as active contract to PARENT;
- `pending_acknowledgement` — version is ready for the contracting Guardian to review;
- `active` — business-active contract;
- `expired` — end date passed under business rules;
- `terminated` — ended early after activation;
- `cancelled` — abandoned before activation.

Allowed high-level transitions:

```text
draft → pending_acknowledgement → active → expired
draft → cancelled
pending_acknowledgement → cancelled
active → terminated
```

Historical versions and terminal contracts remain readable according to retention policy; they are not hard-deleted as an operational action.

## 6. Contract versions and amendments

A legal/business amendment does not mutate historical terms in place.

Use:

- stable `contract_id`;
- monotonically increasing `version_number`;
- immutable ContractVersion after activation;
- `supersedes_version_id` for amendments where applicable;
- effective period per version.

Creating an amendment creates a new draft version. Activating it supersedes the previous active version from the new effective date.

A version may contain structured commercial terms needed by billing, such as:

- service period;
- billing frequency;
- agreed recurring amount in minor units when used;
- due-day/due-rule identifier;
- human-readable non-sensitive title.

Do not copy passport scans or free-form identity data into version metadata.

## 7. Contract acknowledgement and signature boundary

Smart Garden may record:

- version delivered/viewable;
- PARENT acknowledgement timestamp;
- User that acknowledged;
- technical evidence such as server timestamp and safe event identifier.

This is **product acknowledgement**, not a claim of qualified electronic signature.

No QES/УКЭП, simple e-signature legal scheme or external signing provider is asserted by Stage 7. If legal signing is required, it is a separate provider/legal design gate.

## 8. Contract document boundary

Core Stage 7 supports contract document metadata and a future authenticated object reference.

Contract/Version may have:

- `document_status`: `none | available | unavailable`;
- opaque `document_object_id` only when the approved protected storage subsystem exists;
- content hash/checksum metadata if generated by the trusted backend;
- MIME/type and size limits defined by the later storage implementation.

Never store:

- public file URL;
- provider secret;
- local workstation path;
- raw document body in Audit/logs.

Until production storage is approved/configured, contract binary upload/download fails closed. Metadata-only Contracts remain usable.

## 9. Charges

A Charge is a financial obligation under one Contract.

Required business fields:

- UUID;
- Contract;
- optional ContractVersion;
- charge period or service date;
- title/category enum;
- amount_minor;
- currency = `RUB`;
- issue date;
- due date;
- lifecycle state;
- created_by;
- timestamps.

Charge lifecycle:

- `draft`;
- `issued`;
- `cancelled`;
- `corrected`.

An issued Charge is not edited destructively. A correction creates an explicit corrective Charge/event linked to the original.

Settlement is derived separately:

- `unpaid`;
- `partially_paid`;
- `paid`.

`overdue` is a derived condition: outstanding amount > 0 and due date is before the current garden-local date.

## 10. Partial payment and allocation

Payment and Charge are connected through explicit PaymentAllocation rows/events.

Rules:

- one Payment may fund one or more Charges;
- one Charge may receive multiple Payments;
- allocation amount cannot exceed the confirmed available Payment amount;
- allocation cannot make a Charge's paid amount exceed its effective payable amount;
- pending/failed payments do not settle charges;
- allocations to cancelled/corrected-away obligations are rejected or explicitly unwound by a correction operation.

PARENT payment initiation is not part of the provider-neutral core. When a future provider exists, the payment session must target explicit outstanding obligations or an explicit account amount.

## 11. Payments

A Payment records money-status evidence, not card credentials.

Payment sources:

- `provider` — created/updated from a future approved payment integration;
- `manual` — approved offline/manual reconciliation by management.

Payment states:

- `pending`;
- `confirmed`;
- `failed`;
- `reversed`;
- `partially_refunded`;
- `refunded`.

Core metadata may include:

- UUID;
- amount_minor;
- currency;
- source;
- safe external/provider reference;
- provider name enum/string only after an integration is approved;
- occurred/confirmed timestamps;
- recorded_by where manual;
- status.

Never store:

- PAN;
- CVV/CVC;
- full bank account secret;
- bank login/password;
- payment access token;
- raw provider webhook body as business data.

## 12. Idempotency

Every external financial event must be idempotent.

Future provider integrations must enforce a unique tuple equivalent to:

`provider + external_event_id`

Reprocessing the same event returns the prior business result and must not duplicate:

- Payment;
- Refund;
- Receipt;
- Allocation.

Management write APIs that can be safely retried must support an idempotency key or equivalent stable request identifier where duplicate financial effects are possible.

## 13. Debt

For one Contract:

`outstanding = sum(effective issued charge amounts) - sum(valid confirmed allocations)`

`overdue_debt = outstanding portions whose due date is before garden-local today`

Debt is never a manually editable scalar field.

The UI may show:

- total outstanding;
- overdue amount;
- next due date;
- outstanding Charges.

## 14. Overpayment / credit

Overpayment is confirmed money not currently allocated to effective Charges.

It is represented as unapplied confirmed balance, not as a negative Charge.

Core rule:

- Smart Garden does **not** silently auto-apply credit to future Charges.
- DIRECTOR/ADMIN may perform an explicit allocation when business rules permit.
- A future provider flow may propose an allocation, but Backend records it explicitly.

The PARENT cabinet shows overpayment/credit separately from debt.

## 15. Reversal, refund and correction

### Payment reversal

A reversal represents a payment that no longer counts as received, for example provider reversal/chargeback.

It:

- references the original Payment;
- is immutable as an event;
- invalidates/unwinds affected allocations through explicit adjustment records;
- may reopen Charge debt.

### Refund

A Refund is an outgoing financial event linked to a confirmed Payment.

It:

- has its own UUID/status/amount;
- cannot exceed refundable confirmed amount;
- may be partial;
- adjusts allocations explicitly;
- may require a refund receipt/correction receipt depending on later fiscal integration.

### Charge correction

Do not edit an issued historical amount in place.

Create a correction linked to the original Charge and compute the effective obligation from the event history.

## 16. Receipts / fiscal documents

Receipt metadata is linked to the Payment and, where relevant, Refund/correction.

Receipt kinds are provider/fiscal-system-neutral:

- `payment`;
- `refund`;
- `correction`.

Receipt states:

- `registered`;
- `replaced`;
- `unavailable`.

Core fields:

- UUID;
- related payment/refund;
- kind;
- safe external receipt identifier;
- issued_at;
- status;
- optional `replaces_receipt_id`;
- optional protected `document_object_id`.

A corrected/replacement receipt never overwrites the previous receipt row.

## 17. Receipt content

PARENT may download/view receipt content only through authenticated authorization.

Requirements:

- no public URLs;
- no permanent bearer link in UI;
- entitlement checked on every request;
- content not stored in browser persistent storage by Smart Garden code;
- no receipt body in logs or Audit.details;
- expired/withdrawn entitlement is re-evaluated on every request.

Production binary content remains fail-closed until an approved storage design is implemented.

## 18. Parent cabinet

Stage 7 adds these PARENT surfaces:

### My contracts

Show:

- contract number;
- Child;
- status;
- effective dates;
- current version;
- acknowledgement state;
- authenticated document action only when available.

### Balance

Show clearly:

- current outstanding;
- overdue debt;
- overpayment/credit;
- next due amount/date.

### Charges

Show:

- title;
- period;
- amount;
- due date;
- settlement state;
- overdue marker.

### Payments

Show:

- amount;
- date;
- status;
- safe reference;
- allocation summary.

### Receipts

Show:

- receipt date;
- type;
- safe identifier;
- status;
- authenticated download/view action when content exists.

Avoid exposing internal reconciliation identifiers unless needed for support.

## 19. DIRECTOR / ADMIN cabinet

Future management navigation:

- Договоры
- Начисления
- Платежи
- Задолженность
- Сверка
- Чеки

DIRECTOR additionally gets privileged contract lifecycle controls.

The operational dashboard may later show aggregate counts/amounts such as:

- total outstanding;
- overdue amount;
- pending reconciliation count;
- failed/pending payment count.

Do not include parent names, passport data or receipt content in aggregate attention payloads.

## 20. Reconciliation

Reconciliation is the process of matching confirmed money evidence to Smart Garden obligations.

Minimum workflow:

1. list pending/unallocated Payments;
2. inspect safe payment metadata;
3. allocate to eligible Charges;
4. record reconciliation actor/time;
5. show remaining unallocated credit;
6. emit privacy-safe Audit action.

No operator edits raw provider event payloads.

## 21. Notifications

Reuse the existing Notification concept where compatible.

Stage 7 may create notifications for:

- charge issued;
- due date approaching;
- overdue obligation;
- payment confirmed;
- payment failed;
- payment reversed;
- refund confirmed;
- receipt available;
- contract version awaiting acknowledgement.

Notification payload remains minimal and references the business object. It must not duplicate contract text, passport data, payment secrets or receipt content.

## 22. Garden-local date/time

Business date decisions use `Organization.timezone`.

Examples:

- whether a Charge is overdue;
- effective contract date;
- due-date reminders.

Financial event timestamps are stored as timezone-aware instants. UI presents them in garden-local time unless the provider/fiscal document has a legally significant original timestamp that must also be retained.

## 23. Search and filters

Management filters may include:

- Contract status;
- Child UUID/entity selector;
- contracting Guardian entity selector;
- charge due range;
- settlement status;
- overdue only;
- payment state/source;
- reconciliation state;
- receipt state.

Do not put passport number, payment secret or free-text legal content in URLs.

## 24. No hard-delete product action

Normal UI offers no hard delete for:

- activated Contract versions;
- issued Charges;
- confirmed Payments;
- Allocations;
- Refunds/Reversals;
- Receipts.

Drafts may be cancelled/archived according to the implementation contract.

Legal retention/destruction is a separate privileged lifecycle, not a normal business delete button.

## 25. Explicitly not Stage 7 core

Not part of this frozen core product:

- selecting an acquiring/payment provider;
- real payment execution;
- card form hosting;
- production provider credentials;
- qualified electronic signature;
- production object-storage vendor;
- payroll/accounting ERP;
- tax accounting;
- medical billing;
- AI analysis of contract/payment PII;
- entrance/access-control hardware.

## 26. Product acceptance

Future Stage 7 acceptance must demonstrate:

```text
DIRECTOR creates/activates Contract
→ issues Charge
→ confirmed Payment is recorded
→ Payment is allocated
→ balance updates
→ Receipt metadata becomes available
→ eligible PARENT sees contract, balance, payment and receipt
→ non-contracting Guardian is denied
→ TEACHER is denied
→ cross-tenant access is denied
→ history remains auditable without sensitive payload leakage
```

This is technical/product acceptance only.