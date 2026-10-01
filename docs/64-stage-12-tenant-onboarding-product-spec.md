# Stage 12 — Tenant Onboarding Product Specification

**Status:** design proposal for Issue #148; frozen only after the design PR merges.
**Owner:** ONN9IX.
**Implementation:** NOT AUTHORIZED until Stage 6 integrated acceptance is complete.
**Design baseline:** `2e7256f1d856b0da39f9058ccac0b1e344dd1be7`.

## 1. Goal

Define how a real kindergarten becomes a Smart Garden tenant and how its SaaS subscription is represented without coupling commercial billing state to access-control state.

Stage 12 covers the SaaS customer lifecycle of the kindergarten itself.

It does not replace Stage 7 parent contracts/billing.

## 2. Existing tenant invariant

Current Organization is the tenant root.

Existing access lifecycle:

- `active`
- `blocked`
- `archived`

Existing authentication already denies users whose Organization is not active.

Stage 12 preserves this behavior.

## 3. Critical separation

Two independent concepts remain separate:

### Organization access state

Security/operations state controlling whether tenant users may authenticate/use the system.

### SaaS subscription state

Commercial state describing trial, paid term, overdue invoice or cancellation.

A subscription becoming `past_due` MUST NOT automatically set Organization.status to `blocked`.

Reasons:

- operational kindergarten workflows can be safety-critical;
- billing incidents can be temporary or disputed;
- hard lockout could prevent lawful data access/export;
- commercial enforcement requires explicit business policy.

Any Organization block remains an intentional privileged platform-operations action.

## 4. Onboarding model

Initial Stage 12 onboarding is operator-assisted.

Flow:

```text
commercial agreement / approved trial
→ operator validates minimal tenant setup
→ Organization created
→ first DIRECTOR User created
→ temporary password/change-required flow
→ subscription metadata created
→ DIRECTOR signs in and completes setup
```

No public anonymous “create kindergarten” signup is required in core.

## 5. No platform superuser in tenant RBAC

Do not add:

- PLATFORM_ADMIN;
- SUPERADMIN;
- OWNER_GLOBAL

to the existing tenant User.role enum.

Current tenant roles remain:

- DIRECTOR
- ADMIN
- TEACHER
- PARENT

Platform provisioning is an infrastructure/operator concern.

A future browser-based platform control plane requires a separate authentication/RBAC design.

## 6. Organization onboarding fields

Core Organization creation uses only existing/minimal fields:

- name;
- timezone;
- status = active by controlled provisioning.

Do not add speculative:

- INN;
- OGRN;
- legal address;
- banking details;
- license number;
- passport details;
- director civil identity fields

unless a later commercial/legal requirement explicitly proves necessity.

## 7. Initial DIRECTOR bootstrap

Provision exactly one initial DIRECTOR User.

Use existing auth invariants:

- globally normalized unique username;
- password hash only;
- role = DIRECTOR;
- status = active;
- must_change_password = true;
- server-side sessions only.

Temporary password must be delivered through an approved operational channel and never logged.

Stage 12 does not invent email-password-reset or SMS authentication.

## 8. Subscription entity

Freeze a tenant SaaS subscription concept independent of Organization.status.

Conceptual states:

- `trial`
- `active`
- `past_due`
- `cancel_at_period_end`
- `cancelled`

Do not use subscription status as an auth check in core.

## 9. Subscription periods

Conceptual fields:

- plan_code;
- billing_interval;
- currency;
- amount_minor;
- current_period_start;
- current_period_end;
- trial_ends_at;
- cancel_at_period_end;
- cancelled_at;
- status;
- safe external commercial reference if later required.

Core currency:

- RUB.

Allowed billing intervals may include:

- monthly;
- half_year;
- yearly.

Exact offered plans/prices remain commercial configuration, not hard-coded product truth.

## 10. Trial

Trial is a commercial status.

During trial:

- Organization remains active;
- all approved core features follow normal role permissions;
- trial end date may be shown to DIRECTOR.

Trial expiration does not automatically destroy or archive tenant data.

A transition policy is explicit and auditable.

## 11. Active subscription

`active` means the current commercial term is in good standing under Smart Garden's business process.

It does not change RBAC.

DIRECTOR may see:

- plan;
- period;
- next renewal/end date;
- subscription state.

Other tenant roles do not need this information.

## 12. Past due

`past_due` means a commercial payment/invoice issue exists.

Core behavior:

- Organization remains unchanged;
- authentication remains available;
- DIRECTOR sees a clear billing/status notice;
- system may record follow-up/admin process metadata;
- no automatic tenant lockout.

A future commercial policy may define grace periods or restrictions, but that requires explicit design before implementation.

## 13. Cancel at period end

`cancel_at_period_end` means service is expected to terminate commercially after the current period.

Before period end:

- Organization remains active;
- normal service continues;
- DIRECTOR sees effective end date.

No data is deleted automatically.

## 14. Cancelled

`cancelled` means the SaaS commercial agreement is no longer active.

This still does not automatically imply:

- Organization.status = archived;
- user deletion;
- immediate physical data destruction.

Offboarding is a separate controlled process.

## 15. Organization blocked

Existing Organization.status = blocked remains a security/operations control.

Possible reasons may include:

- security incident;
- explicit administrative/legal action;
- approved platform operations decision.

Do not reuse `blocked` as a generic invoice collection mechanism.

Blocking affects all tenant users and therefore requires explicit privileged action and Audit.

## 16. Organization archived

Archived represents completed tenant lifecycle at the application level.

Archive is not immediate legal erasure.

Before archive:

- export/retention obligations must be considered;
- sessions revoked;
- new logins denied;
- data retained according to approved policy.

Physical destruction happens only through approved retention/destruction process.

## 17. DIRECTOR subscription surface

Suggested management section:

`Settings → Subscription`

Read-only core fields:

- plan name/code;
- current state;
- trial end;
- current billing period;
- amount;
- billing interval;
- cancellation effective date where relevant;
- support/contact action.

No payment card form in Stage 12 core.

## 18. Subscription actions

Core tenant UI is read-only.

DIRECTOR cannot directly:

- edit plan price;
- mark subscription paid;
- change tenant access status;
- create another Organization;
- forge renewal period.

Future self-service plan change/cancel can be designed after payment/provider strategy exists.

## 19. Commercial billing provider boundary

Stage 12 core does not:

- charge the kindergarten;
- process cards;
- generate fiscal receipt;
- connect acquiring provider;
- automatically reconcile invoices.

Commercial provider integration is a separate future gate.

Stage 7 parent billing remains a separate product domain.

## 20. Parent surcharge business model

A kindergarten may commercially include Smart Garden cost in its parent contract.

Stage 12 does not hard-code a specific surcharge such as 300 RUB per parent.

That is a sales/pricing strategy, not tenant-auth architecture.

If represented in product, it belongs to explicit Stage 7 contract/billing configuration later.

## 21. Plan entitlements

Stage 12 core does not introduce complex feature gating by plan.

Preferred initial commercial model:

- one primary product plan;
- commercial differences expressed by term/price rather than hidden role capabilities.

If multiple plans later have different features, entitlement logic needs a separate design and tests.

## 22. Provisioning idempotency

Operator-assisted provisioning must be idempotent.

Retrying a provisioning command must not create:

- duplicate Organization;
- duplicate initial DIRECTOR;
- duplicate subscription.

A stable operator request/provisioning reference may be used internally without containing PII.

## 23. Onboarding success criteria

A tenant is considered provisioned when:

- Organization exists;
- timezone valid;
- first DIRECTOR exists;
- DIRECTOR must_change_password = true;
- subscription metadata exists;
- no real child/parent data is preloaded;
- tenant can authenticate after temporary password change;
- Audit/provisioning record exists where required.

## 24. Demo/test tenants

Dev/test/preview may create synthetic organizations automatically.

Synthetic tenant bootstrap remains clearly separated from production provisioning.

Never clone production tenant data into demo.

## 25. Offboarding flow

Conceptual offboarding:

```text
commercial cancellation
→ retention/export review
→ optional scheduled archive
→ revoke active sessions
→ Organization archived/blocked only by approved operation
→ data retained/destructed per policy
```

No one-click destructive deletion in ordinary tenant UI.

## 26. Product acceptance target

Future technical acceptance demonstrates:

```text
operator provisions Organization
→ first DIRECTOR created
→ temporary password change required
→ Subscription=trial/active
→ DIRECTOR sees subscription
→ ADMIN/TEACHER/PARENT cannot manage it
→ past_due does not block Organization
→ explicit Organization block denies login
→ cancelled subscription does not silently erase tenant
```

Technical acceptance does not define the final commercial contract or legal retention periods.