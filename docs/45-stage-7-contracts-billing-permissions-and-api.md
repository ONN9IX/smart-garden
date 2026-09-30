# Stage 7 — Contracts, Billing and Receipts Permissions and API

**Status:** design proposal for Issue #137; frozen only after the design PR merges.
**Owner:** ONN9IX.
**Implementation:** NOT AUTHORIZED until Stage 6 integrated acceptance is complete.
**API conventions:** `/api/v1`, JSON `snake_case`, UUID identifiers, server-owned tenant/actor fields.

## 1. Authorization invariants

1. Authentication remains the existing server-side session + HttpOnly cookie.
2. Tenant is derived only from authenticated User.
3. Client-supplied `organization_id`, actor, payer or owner never changes authority.
4. Frontend visibility is not authorization.
5. Object queries are always tenant-scoped before role/business checks.
6. Cross-tenant and hidden-resource behavior follows the active non-disclosure contract.
7. PARENT financial eligibility is stricter than ordinary Child access.
8. TEACHER has no Stage 7 routes.

## 2. Stage 7 permission matrix

| Capability | DIRECTOR | ADMIN | TEACHER | PARENT |
|---|---|---|---|---|
| List own-tenant contract operational metadata | Yes | Yes | No | Own eligible only |
| Create draft Contract | Yes | No | No | No |
| Change contracting Guardian/Child while draft | Yes | No | No | No |
| Activate Contract | Yes | No | No | No |
| Amend active Contract | Yes | No | No | No |
| Terminate/cancel Contract | Yes | No | No | No |
| Read restricted identity data | Later explicit gate only | No | No | Own-self only if separately designed |
| Read authenticated contract document | Yes | Operational need only if explicitly allowed | No | Own eligible only |
| Create/issue Charge | Yes | Yes | No | No |
| Correct/cancel Charge | Yes | Yes | No | No |
| Read balances/debt | Yes | Yes | No | Own eligible only |
| Record manual Payment metadata | Yes | Yes | No | No |
| Reconcile/allocate Payment | Yes | Yes | No | No |
| Reverse/refund Payment | Yes | No | No | No |
| Read payment history | Yes | Yes | No | Own eligible only |
| Register/read Receipt metadata | Yes | Yes | No | Own eligible only |
| Read authenticated Receipt content | Yes | Yes if operationally required | No | Own eligible only |
| Read Stage 7 Audit | Yes | No | No | No |
| Configure provider/storage integration | Future privileged gate | No | No | No |

## 3. PARENT eligibility function

A PARENT may read a Contract-domain object only when Backend proves all of:

```text
authenticated_user.role == PARENT
guardian(user) == contract.contracting_guardian_id
active ChildGuardian(guardian, contract.child_id)
contract.organization_id == authenticated_user.organization_id
resource.contract_id == contract.id
```

If any relation becomes inactive, the next request loses access.

A sibling Child, another Guardian for the same Child, or another Contract in the tenant does not inherit access.

## 4. Proposed data model

This document freezes names and semantics, not physical ORM implementation.

### Contract

- `id: UUID`
- `organization_id: UUID` — server-owned
- `child_id: UUID`
- `contracting_guardian_id: UUID`
- `contract_number: string`
- `status: draft | pending_acknowledgement | active | expired | terminated | cancelled`
- `current_version_id: UUID | null`
- `created_by: UUID` — server-owned
- `created_at`
- `updated_at`

Constraints:

- Child and Guardian must belong to same tenant.
- Guardian must have an active ChildGuardian relationship to Child at creation/activation.
- Contract number is unique within Organization according to the implementation migration.
- No raw passport fields.

### ContractVersion

- `id: UUID`
- `contract_id: UUID`
- `version_number: integer`
- `supersedes_version_id: UUID | null`
- `effective_from: date`
- `effective_to: date | null`
- `billing_frequency: enum | null`
- `recurring_amount_minor: integer | null`
- `currency: RUB`
- `due_rule: enum/string contract`
- `title: string`
- `acknowledged_by_user_id: UUID | null`
- `acknowledged_at: timestamp | null`
- `document_status: none | available | unavailable`
- `document_object_id: UUID | null`
- `created_by: UUID`
- `created_at`

Activated versions are immutable except server-controlled acknowledgement/document-state transitions explicitly allowed by the implementation contract.

### Charge

- `id: UUID`
- `organization_id: UUID`
- `contract_id: UUID`
- `contract_version_id: UUID | null`
- `service_period_start: date | null`
- `service_period_end: date | null`
- `title: string`
- `kind: recurring_service | one_time | correction`
- `amount_minor: integer`
- `currency: RUB`
- `issued_on: date | null`
- `due_on: date | null`
- `status: draft | issued | cancelled | corrected`
- `corrects_charge_id: UUID | null`
- `created_by: UUID`
- `created_at`
- `updated_at`

No client-supplied settlement amount is authoritative.

### Payment

- `id: UUID`
- `organization_id: UUID`
- `contract_id: UUID`
- `amount_minor: integer`
- `currency: RUB`
- `source: provider | manual`
- `status: pending | confirmed | failed | reversed | partially_refunded | refunded`
- `safe_external_reference: string | null`
- `provider_code: string | null`
- `external_event_id: string | null`
- `occurred_at: timestamp | null`
- `confirmed_at: timestamp | null`
- `recorded_by: UUID | null`
- `created_at`
- `updated_at`

No PAN/CVV/token/raw webhook body.

### PaymentAllocation

- `id: UUID`
- `payment_id: UUID`
- `charge_id: UUID`
- `amount_minor: integer`
- `status: active | unwound`
- `created_by: UUID | null`
- `created_at`
- `unwound_at: timestamp | null`
- `unwound_by_event_id: UUID | null`

Allocation mutations are represented as explicit events/rows, not destructive amount edits.

### PaymentAdjustment

Represents reversal/refund/correction affecting received money.

- `id: UUID`
- `payment_id: UUID`
- `kind: reversal | refund`
- `amount_minor: integer`
- `status: pending | confirmed | failed`
- `safe_external_reference: string | null`
- `external_event_id: string | null`
- `occurred_at`
- `created_by: UUID | null`
- `created_at`

### Receipt

- `id: UUID`
- `organization_id: UUID`
- `payment_id: UUID | null`
- `payment_adjustment_id: UUID | null`
- `kind: payment | refund | correction`
- `status: registered | replaced | unavailable`
- `safe_external_receipt_id: string`
- `issued_at: timestamp`
- `replaces_receipt_id: UUID | null`
- `document_object_id: UUID | null`
- `created_at`

### FinancialIdempotencyRecord

Implementation may use a dedicated record/table or enforce equivalent unique keys.

Required semantics:

- unique provider/external event identity;
- request result can be recovered;
- duplicate event creates no second financial effect.

## 5. Derived financial fields

Do not persist user-editable debt or paid scalars as source of truth.

For each Charge:

- `effective_amount_minor`
- `allocated_confirmed_minor`
- `outstanding_minor`
- `settlement_status`
- `is_overdue`

For each Contract:

- `outstanding_minor`
- `overdue_minor`
- `unapplied_credit_minor`

These are derived from effective Charges, confirmed Payments, active Allocations and confirmed Adjustments.

## 6. Management Contract API

Proposed routes:

- `GET /api/v1/contracts`
- `POST /api/v1/contracts`
- `GET /api/v1/contracts/{contract_id}`
- `PATCH /api/v1/contracts/{contract_id}` — draft-only fields
- `POST /api/v1/contracts/{contract_id}/submit-for-acknowledgement`
- `POST /api/v1/contracts/{contract_id}/activate`
- `POST /api/v1/contracts/{contract_id}/terminate`
- `POST /api/v1/contracts/{contract_id}/cancel`
- `POST /api/v1/contracts/{contract_id}/versions`
- `GET /api/v1/contracts/{contract_id}/versions`
- `GET /api/v1/contracts/{contract_id}/versions/{version_id}`

DIRECTOR only for writes unless explicitly stated otherwise.

No route accepts `organization_id` as authority.

## 7. Contract document API boundary

Proposed protected routes once storage exists:

- `GET /api/v1/contracts/{contract_id}/versions/{version_id}/document`
- `POST /api/v1/contracts/{contract_id}/versions/{version_id}/document` — DIRECTOR only, only after approved storage gate

Before approved storage configuration:

- upload returns fail-closed service/configuration error;
- content GET returns unavailable unless an approved object already exists;
- no public URL is returned.

The API returns authenticated content/stream or a short-lived server-mediated mechanism whose authorization is revalidated. Permanent public object URLs are forbidden.

## 8. Charge API

Proposed routes:

- `GET /api/v1/billing/charges`
- `POST /api/v1/billing/charges`
- `GET /api/v1/billing/charges/{charge_id}`
- `PATCH /api/v1/billing/charges/{charge_id}` — draft only
- `POST /api/v1/billing/charges/{charge_id}/issue`
- `POST /api/v1/billing/charges/{charge_id}/cancel`
- `POST /api/v1/billing/charges/{charge_id}/correct`

DIRECTOR/ADMIN may operate according to the permission matrix. Manual reversal/refund commands are DIRECTOR-only; provider-originated reversals/refunds may be applied server-side after authenticated provider-event validation.

Issued amount/date/contract history is not overwritten by generic PATCH.

## 9. Payment API

Core management routes:

- `GET /api/v1/billing/payments`
- `POST /api/v1/billing/payments/manual`
- `GET /api/v1/billing/payments/{payment_id}`
- `POST /api/v1/billing/payments/{payment_id}/allocate`
- `POST /api/v1/billing/payments/{payment_id}/reverse` — DIRECTOR only for manual management action
- `POST /api/v1/billing/payments/{payment_id}/refund` — DIRECTOR only for manual management action

A manual Payment request includes only business-safe fields such as:

- contract_id;
- amount_minor;
- occurred_at;
- safe external/reference text with strict length/format;
- optional intended Charge allocation.

It never includes card/bank secrets.

## 10. Provider event boundary

Future provider integration route is reserved conceptually, not implemented/frozen to a vendor-specific shape.

Example namespace:

`POST /api/v1/integrations/payments/{provider_code}/events`

Requirements:

- provider authentication/signature verification occurs before business processing;
- raw secrets are never copied to Audit;
- event identity is idempotent;
- tenant/Contract mapping comes from trusted server/provider mapping, not arbitrary client organization input;
- unsupported/ambiguous events fail closed;
- provider-specific code stays behind a service adapter.

Provider selection requires a separate gate.

## 11. Receipt API

Management:

- `GET /api/v1/billing/receipts`
- `GET /api/v1/billing/receipts/{receipt_id}`
- `POST /api/v1/billing/receipts/register` — manual/provider-adapter use under explicit rules
- `GET /api/v1/billing/receipts/{receipt_id}/content`

PARENT content entitlement is not inherited from management endpoint visibility; it is separately checked.

## 12. Parent API

Proposed PARENT routes:

- `GET /api/v1/parent/contracts`
- `GET /api/v1/parent/contracts/{contract_id}`
- `POST /api/v1/parent/contracts/{contract_id}/versions/{version_id}/acknowledge`
- `GET /api/v1/parent/contracts/{contract_id}/document`
- `GET /api/v1/parent/billing/summary`
- `GET /api/v1/parent/billing/charges`
- `GET /api/v1/parent/billing/charges/{charge_id}`
- `GET /api/v1/parent/billing/payments`
- `GET /api/v1/parent/billing/payments/{payment_id}`
- `GET /api/v1/parent/billing/receipts`
- `GET /api/v1/parent/billing/receipts/{receipt_id}/content`

Stage 7 core has no `/parent/pay` write until a provider/payment-session design is approved.

## 13. Parent acknowledgement API

Acknowledgement request contains no actor or Guardian ID.

Backend derives User and eligible Contract, records:

- user_id;
- version_id;
- acknowledged_at;
- request/audit correlation ID if safe.

Repeated acknowledgement is idempotent.

Acknowledgement does not become a legal e-signature claim automatically.

## 14. Query/filter contract

Management list routes may accept:

- `status`;
- `child_id`;
- `guardian_id`;
- `contract_id`;
- `due_from`;
- `due_to`;
- `overdue`;
- `payment_status`;
- `reconciliation_status`;
- pagination.

PARENT routes do not accept arbitrary Guardian/User IDs.

Avoid PII-rich free-text query logging.

## 15. Response minimization

### Contract list

Management ordinary list:

- id;
- contract_number;
- Child minimal presentation;
- contracting Guardian minimal presentation;
- status;
- effective dates;
- balance summary.

No passport/identity-document values.

PARENT list:

- own contract id/number;
- linked Child minimal presentation;
- status;
- current version/effective dates;
- acknowledgement/document availability.

### Payment list

Return:

- id;
- amount;
- currency;
- source;
- status;
- occurred/confirmed time;
- safe reference;
- allocation summary.

Never return provider credentials, token, raw event or full bank/card details.

### Receipt list

Return:

- id;
- kind;
- status;
- issued_at;
- safe receipt identifier;
- content availability.

No storage URL.

## 16. Error and non-disclosure behavior

Use the current API error envelope and active Stage 1–6 conventions.

At minimum:

- unauthenticated → auth error;
- wrong role on visible route → 403;
- cross-tenant/hidden resource → current non-disclosure behavior;
- PARENT non-entitled Contract/Payment/Receipt → hidden-resource behavior;
- invalid state transition → stable validation/business error;
- duplicate idempotency event → existing result/no duplicate;
- provider/storage not configured → fail-closed structured error.

Never expose SQL, stack trace, provider secret or object-storage key.

## 17. Concurrency and financial consistency

Implementation must use transactional protection for operations that can double-spend or double-allocate.

At minimum:

- Payment confirmation;
- allocation;
- refund/reversal;
- Charge correction;
- idempotent provider event application.

Two concurrent allocations cannot allocate more than the Payment or Charge allows.

The exact SQL locking/constraint strategy is implementation detail, but the invariant is frozen.

## 18. Audit actions

Stage 7 requires explicit allowlisted action names or equivalent stable names for:

- `contract.created`
- `contract.submitted`
- `contract.activated`
- `contract.amended`
- `contract.terminated`
- `contract.cancelled`
- `contract.acknowledged`
- `charge.created`
- `charge.issued`
- `charge.corrected`
- `charge.cancelled`
- `payment.manual_recorded`
- `payment.confirmed`
- `payment.allocated`
- `payment.reversed`
- `payment.refunded`
- `receipt.registered`
- `receipt.replaced`
- `restricted_identity.accessed` only if that future data class exists

Safe Audit.details may contain:

- business object UUIDs;
- amount_minor/currency where needed for financial accountability;
- status_before/status_after;
- changed_fields names;
- provider_code;
- safe event/reference identifiers subject to privacy review.

Audit.details must not contain:

- passport series/number;
- scans;
- payment secrets;
- card data;
- raw webhook;
- contract body;
- receipt body;
- bank account credentials;
- document object secret/path.

## 19. Notification event contract

Business services may emit a minimal internal notification event:

- recipient_user_id server-derived;
- kind enum;
- entity_type;
- entity_id;
- created_at.

Do not copy full charge/contract/receipt content into Notification rows.

## 20. Restricted identity extension boundary

Raw passport/identity-document fields are **not part of the Stage 7 core schema frozen by this Issue**.

If legally/business-wise required, a later serialized design must define:

- exact minimum fields;
- legal purpose/basis;
- role and field masking;
- encryption/key management;
- read Audit;
- retention/destruction;
- backup handling;
- export;
- migration.

Until then, contract creation uses existing Guardian identity plus contract/document references and does not invent passport fields.

## 21. Required negative tests for future implementation

### Tenant

Reject/hide foreign:

- Contract;
- ContractVersion;
- Charge;
- Payment;
- Allocation;
- Adjustment;
- Receipt.

### Role

- TEACHER → every Stage 7 route = denied.
- PARENT → every management write = denied.
- ADMIN → Contract party/lifecycle privileged writes = denied.
- ADMIN → restricted identity read = denied.
- ADMIN → Stage 7 Audit read = denied.

### Parent entitlement

- linked but non-contracting Guardian cannot read financial resources;
- inactive ChildGuardian relation loses access on next request;
- forged guardian_id/user_id does not grant access;
- receipt/content cannot be enumerated by UUID.

### Financial integrity

- duplicate provider event creates one effect;
- pending/failed Payment does not settle Charge;
- allocation cannot exceed Payment available amount;
- allocation cannot overpay Charge;
- refund cannot exceed refundable amount;
- reversal reopens relevant obligation;
- issued Charge is not mutated by generic update;
- corrected financial history remains visible;
- concurrent duplicate writes preserve invariants.

### Privacy

- no PAN/CVV accepted by schemas;
- raw provider body absent from logs/Audit;
- no document public URL;
- no passport fields in core;
- safe error responses only.

## 22. Required browser flows for future implementation

DIRECTOR:

```text
login
→ Contracts
→ create Contract
→ submit/activate
→ create + issue Charge
→ record/observe Payment
→ allocate/reconcile
→ see balance
→ register/view Receipt metadata
→ Audit
→ logout
```

ADMIN:

```text
login
→ Contracts operational list
→ Charges
→ Payments
→ Reconciliation
→ Receipts
→ verify privileged Contract controls absent
→ logout
```

PARENT:

```text
login
→ My contracts
→ acknowledge current version
→ Balance
→ Charges
→ Payments
→ Receipts
→ authenticated receipt/document content when configured
→ logout
```

TEACHER:

```text
login
→ no Stage 7 navigation
→ direct Stage 7 API/page attempt denied
```

## 23. Compatibility

Stage 7 must preserve:

- current auth/session;
- current tenant isolation;
- existing PARENT child access;
- Stage 6 teacher-domain privacy;
- DIRECTOR-only Audit read;
- Organization timezone semantics;
- synthetic-only dev/test/preview.

No Stage 7 API may weaken Stage 1–6 protections.