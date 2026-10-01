# Stage 12 — Tenant Onboarding Delivery Plan

**Status:** design proposal for Issue #148; frozen only after the design PR merges.
**Owner:** ONN9IX.
**Implementation:** NOT AUTHORIZED until Stage 6 integrated acceptance is complete.

## 1. Runtime prerequisite

No Stage 12 implementation before:

1. Stage 6 integrated acceptance/freeze;
2. current Organization/User/Auth behavior is revalidated;
3. current migration head is recorded;
4. commercial plan fields are explicitly approved;
5. a serialized migration lane is free.

## 2. Design gate

Issue #148 owns exactly:

- docs/64-stage-12-tenant-onboarding-product-spec.md
- docs/65-stage-12-tenant-subscription-permissions-and-api.md
- docs/66-stage-12-tenant-onboarding-data-privacy.md
- docs/67-stage-12-tenant-onboarding-delivery-plan.md

No runtime code, migrations, tests, CI, dependencies or shared coordination edits.

## 3. Implementation priority

Stage 12 is important for pilot/commercial readiness but should not preempt the core product path.

Preferred sequence after Stage 6:

1. Stage 10 protected-storage foundation;
2. Stage 7 financial foundation/cabinet;
3. Stage 8 parent consolidation;
4. Stage 12 tenant onboarding/subscription;
5. Stage 11 development-support implementation unless a psychology pilot moves it earlier;
6. Stage 9 kiosk implementation as coordination permits.

Master Chat may reorder product implementation when shared migration/write-set conflicts are resolved.

## 4. Preflight

Read only current:

- Organization model;
- User model;
- auth/session services;
- user account bootstrap logic;
- management Settings;
- Audit;
- model registry/migration head;
- configuration/secrets;
- synthetic seed/provisioning helpers.

Confirm:

- Organization status semantics remain active/blocked/archived;
- subscription state is separate;
- temporary-password flow can be reused;
- no platform role is required;
- provisioning can be operator-controlled without public API.

## 5. S12-TENANT-ONBOARDING implementation Issue

Preferred one major serialized Issue:

`S12-TENANT-ONBOARDING — operator provisioning and SaaS subscription lifecycle`

One branch, one migration, one PR.

Expected schema:

- TenantSubscription;
- unique one-current-subscription relationship to Organization;
- status/interval/amount/period constraints;
- optional stable provisioning/idempotency record if required.

Do not modify Organization.status enum unless an independent need is proven.

## 6. Migration rule

Prefer exactly one Stage 12 migration.

No parallel Alembic heads.

If another Foundation owns the migration lane, wait and rebase.

## 7. Provisioning implementation

Preferred initial production mechanism:

- backend management command or tightly controlled operator function;
- not exposed through ordinary /api/v1 tenant routes;
- uses normal application DB/model services;
- no browser platform console required.

Required properties:

- atomic;
- idempotent;
- safe logs;
- temporary-password hash only;
- synthetic test mode.

## 8. Provisioning transaction

Implementation flow:

1. validate input;
2. normalize/check username;
3. validate Organization timezone;
4. validate plan/amount/interval;
5. check provisioning idempotency;
6. create Organization;
7. create initial DIRECTOR;
8. create TenantSubscription;
9. write safe Audit/operator event;
10. commit;
11. securely hand temporary credential to operator workflow.

No Child/Guardian/demo business data is created for a real tenant.

## 9. DIRECTOR subscription UI

Add read-only Settings surface.

Display:

- plan;
- subscription state;
- trial end;
- current period;
- billing interval;
- amount/currency;
- cancellation effective state/date.

Do not display:

- provider secrets;
- internal operator notes;
- another tenant information.

## 10. Tenant-side write restrictions

Frontend has no:

- change price button;
- mark paid button;
- block tenant button;
- create tenant button;
- alter subscription state button.

These remain operator-controlled in core.

## 11. Subscription state service

Implement one state-transition service with explicit allowed transitions.

Every transition:

- tenant-scoped by target Organization;
- validates prior state;
- records actor/operator context safely;
- is auditable;
- does not modify Organization.status automatically.

## 12. Past-due behavior

Tests must prove:

- transition active → past_due succeeds;
- Organization remains active;
- current users remain governed only by existing auth rules;
- DIRECTOR sees past_due state;
- TEACHER/PARENT do not receive commercial state.

No hidden automatic lockout job.

## 13. Cancellation behavior

Tests must prove:

- cancel_at_period_end preserves normal tenant access;
- cancelled does not archive Organization;
- cancelled does not delete Users/data;
- offboarding is separate.

## 14. Explicit Organization blocking

Do not redesign existing auth checks.

If Stage 12 includes an operator block helper, it must be separate from subscription service.

Blocking should:

- set Organization.status under privileged operator process;
- invalidate/revoke sessions according to existing security conventions;
- audit safe reason code;
- never be triggered merely by past_due.

## 15. Offboarding runbook

Stage 12 should add or prepare a future operational runbook covering:

- cancellation confirmation;
- authorized export request;
- retention review;
- session revocation;
- archive decision;
- protected-object implications;
- backup retention;
- eventual approved destruction.

Do not implement destructive automation before legal/business retention rules are approved.

## 16. Synthetic provisioning

Provide deterministic synthetic/test provisioning.

It may create:

- fake Organization;
- fake DIRECTOR username;
- fake subscription.

It must not use production names or credentials.

## 17. Required backend tests

Provisioning:

- creates Organization + DIRECTOR + subscription atomically;
- duplicate provisioning reference creates no duplicate;
- duplicate username fails safely;
- invalid timezone fails;
- temporary password not logged/persisted plaintext.

Subscription:

- valid transitions;
- invalid transitions rejected;
- integer RUB amount;
- wrong interval/currency rejected;
- one current subscription per tenant;
- past_due does not block;
- cancelled does not archive.

RBAC:

- DIRECTOR reads own subscription;
- ADMIN denied in core;
- TEACHER denied;
- PARENT denied;
- foreign tenant hidden.

Auth regression:

- Organization blocked still denies login;
- active Organization remains login-capable independent of subscription status.

## 18. Required browser E2E

DIRECTOR:

```text
login
→ Settings
→ Subscription
→ sees own plan/status/period
→ no edit/pay/block controls
```

ADMIN/TEACHER/PARENT:

- subscription page/navigation absent or denied according to implementation contract.

Commercial state tests should use synthetic tenants only.

## 19. CI/regression

Keep green:

- auth/session;
- temporary-password change;
- Organization blocked behavior;
- tenant isolation;
- Stage 1–6 roles;
- Stage 5 security/backup;
- current Settings;
- Stage 7 parent billing separation.

No weakening auth to support provisioning.

## 20. Future platform control plane

A browser UI for Smart Garden operators is deferred.

It requires separate design for:

- platform identity;
- MFA;
- tenant switching;
- least privilege;
- access audit;
- support impersonation policy;
- emergency access;
- network restrictions.

Do not implement global operator access as a normal tenant User.

## 21. Future SaaS payment integration

Separate future gate:

`S12-SAAS-BILLING-PROVIDER`

It must decide:

- provider;
- invoice/payment flow;
- webhook authentication;
- idempotency;
- fiscal/tax responsibilities;
- credentials;
- commercial reconciliation;
- privacy/data flow.

Stage 12 core can work with manual operator-updated subscription metadata before this integration.

## 22. Pricing configuration

Do not hard-code commercial prices into application logic beyond synthetic fixtures.

Plan codes and prices should be operator/configuration data under controlled change.

A specific parent surcharge is not part of Stage 12.

## 23. STOP conditions

Return to Master Chat if implementation requires:

- PLATFORM_ADMIN/SUPERADMIN role in tenant User;
- public anonymous tenant signup;
- automated Organization block for past_due;
- payment-card storage;
- payment provider selection;
- legal/company PII fields not frozen by design;
- second migration head;
- auth/session redesign;
- automatic destructive offboarding;
- real customer data in dev/test.

## 24. Ordinary defect rule

Fix in same implementation branch:

- subscription state validation bug;
- read-only UI issue;
- provisioning idempotency bug;
- safe error formatting;
- missing test;
- CI failure caused by current change.

Architecture/RBAC/payment/legal expansion returns to Master Chat.

## 25. Validation before PR

Backend:

- ruff;
- Stage 12 targeted tests;
- migration round trip;
- auth/tenant regression.

Frontend:

- lint;
- build;
- DIRECTOR subscription E2E.

Also:

- git diff --check;
- exact write-set;
- secret/plaintext-password inspection;
- synthetic-data review;
- full required CI.

## 26. S12-ACCEPTANCE

Technical acceptance verifies:

- controlled tenant provisioning;
- initial DIRECTOR bootstrap;
- subscription lifecycle;
- tenant/subscription separation;
- past_due no auto-block;
- cancellation no auto-delete;
- tenant RBAC;
- privacy-safe credential handling;
- synthetic-only tests;
- frozen auth regression.

## 27. Real customer readiness remains separate

Before first commercial tenant:

- commercial contract;
- operator access process;
- secure credential delivery;
- account recovery;
- hosting/privacy readiness;
- retention/offboarding;
- support process;
- billing/invoice process;
- legal/tax review as applicable.

Technical acceptance does not substitute for those decisions.