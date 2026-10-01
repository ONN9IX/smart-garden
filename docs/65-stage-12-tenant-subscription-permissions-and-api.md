# Stage 12 — Tenant Subscription Permissions and API

**Status:** design proposal for Issue #148; frozen only after the design PR merges.
**Owner:** ONN9IX.
**Implementation:** NOT AUTHORIZED until Stage 6 integrated acceptance is complete.

## 1. Authorization model

Tenant application users are not platform operators.

The existing tenant roles remain:

- DIRECTOR
- ADMIN
- TEACHER
- PARENT

Stage 12 adds no tenant role for platform provisioning.

## 2. Tenant-side permissions

### DIRECTOR

May read the Organization's own subscription summary.

May not:

- create tenants;
- modify subscription status directly;
- change commercial amount/period;
- mark invoice/payment as paid;
- block/archive Organization through subscription UI.

### ADMIN

No subscription management in core.

Optional read-only visibility may be omitted entirely to minimize commercial data spread.

### TEACHER / PARENT

No SaaS subscription access.

## 3. Platform operator boundary

Provisioning/subscription writes are not ordinary tenant HTTP APIs.

Preferred initial implementation:

- controlled management command / operator procedure;
- authenticated infrastructure access outside tenant User sessions;
- explicit operational logging;
- no public endpoint.

A future web control plane requires separate auth/RBAC design.

## 4. Proposed data model

Conceptual `TenantSubscription`:

- `id: UUID`
- `organization_id: UUID`
- `plan_code: string`
- `status: trial | active | past_due | cancel_at_period_end | cancelled`
- `billing_interval: monthly | half_year | yearly`
- `currency: RUB`
- `amount_minor: integer`
- `trial_ends_at: timestamp | null`
- `current_period_start: timestamp | null`
- `current_period_end: timestamp | null`
- `cancel_at_period_end: bool`
- `cancelled_at: timestamp | null`
- `safe_external_reference: string | null`
- `created_at`
- `updated_at`

One current subscription per Organization in core.

## 5. Organization relationship

Organization remains authoritative for tenant access:

- active;
- blocked;
- archived.

TenantSubscription status must not be read by auth middleware to decide whether a User is authenticated.

In particular:

`past_due != blocked`

and:

`cancelled != archived`

without an explicit separate operations action.

## 6. DIRECTOR read API

Proposed:

`GET /api/v1/settings/subscription`

DIRECTOR-only.

Response:

- plan_code;
- status;
- billing_interval;
- currency;
- amount_minor;
- trial_ends_at;
- current_period_start;
- current_period_end;
- cancel_at_period_end;
- cancelled_at.

Do not expose provider credentials or internal operator notes.

## 7. No tenant write API in core

Do not add ordinary routes such as:

- POST /settings/subscription/pay
- PATCH /settings/subscription/status
- POST /organizations
- PATCH /organizations/{id}/status

for tenant Users as part of Stage 12 core.

Provisioning/subscription writes belong to the operator boundary.

## 8. Provisioning command contract

Conceptual operator command input:

- organization_name;
- organization_timezone;
- initial_director_username;
- temporary_password supplied securely;
- plan_code;
- billing_interval;
- amount_minor;
- currency;
- trial/period dates;
- stable provisioning reference.

Do not accept existing tenant IDs from untrusted client UI.

## 9. Provisioning transaction

Provisioning should be atomic where practical:

1. validate timezone;
2. validate normalized username uniqueness;
3. create Organization;
4. create initial DIRECTOR;
5. create TenantSubscription;
6. write safe provisioning Audit/operations event;
7. commit.

If any required step fails, do not leave a partially usable tenant.

## 10. Temporary password

Store only password hash.

Never write plaintext password to:

- logs;
- Audit;
- provisioning record;
- database field;
- GitHub;
- screenshots.

Initial DIRECTOR must have `must_change_password=true`.

## 11. Subscription state transitions

Allowed conceptual transitions:

- trial → active
- trial → cancelled
- active → past_due
- past_due → active
- active → cancel_at_period_end
- past_due → cancel_at_period_end
- cancel_at_period_end → active
- cancel_at_period_end → cancelled

Any exceptional transition is operator-controlled and audited.

## 12. No automatic access transition

Subscription state change does not automatically modify:

- Organization.status;
- User.status;
- AuthSession.

A later commercial-enforcement policy may explicitly define a manual/automated bridge, but that is outside Stage 12 core.

## 13. Explicit Organization blocking

If platform operations intentionally blocks a tenant for security/legal reasons, use the existing Organization access state.

That action must:

- require privileged operator process;
- record reason code, not unnecessary free text;
- revoke active sessions where current architecture allows/needs it;
- be separately auditable.

Do not call this action from ordinary subscription transition code.

## 14. Cancellation

When subscription becomes cancelled:

- no automatic deletion;
- no automatic Organization archive;
- no automatic User archive.

The offboarding process decides access and retention separately.

## 15. Commercial reference

A safe external commercial reference may identify:

- invoice/account/customer record in a future billing system.

It must not contain:

- payment card data;
- bank credential;
- full contract text;
- secret token.

Provider-specific IDs remain optional until a provider exists.

## 16. Price representation

Use integer minor units.

Do not use floating point.

Core currency is RUB.

Pricing is server/operator-owned.

Tenant UI never submits authoritative amount.

## 17. Time handling

Commercial periods are timezone-aware instants.

DIRECTOR UI may render them in Organization.timezone.

Billing status should not depend on browser clock.

## 18. Audit / operator event

At minimum record safe state transitions:

- tenant.provisioned
- subscription.created
- subscription.activated
- subscription.past_due
- subscription.cancel_scheduled
- subscription.cancelled
- organization.blocked
- organization.archived

Audit details contain:

- organization UUID;
- subscription UUID;
- status before/after;
- plan code;
- period dates;
- amount/currency where justified;
- safe operator/provisioning reference.

Never include password or secret.

## 19. Error handling

Provisioning must fail safely for:

- duplicate username;
- invalid timezone;
- invalid state transition;
- invalid negative amount;
- unsupported currency/interval;
- duplicate provisioning reference.

No error should leak password/hash/secret.

## 20. Required negative tests

Future implementation:

- DIRECTOR cannot create Organization;
- DIRECTOR cannot patch subscription;
- ADMIN/TEACHER/PARENT cannot read subscription endpoint;
- past_due does not change Organization.status;
- cancelled does not archive Organization automatically;
- blocking Organization still denies auth as frozen;
- duplicate provisioning is idempotent/no duplicate tenant;
- plaintext password absent from logs/Audit;
- invalid timezone rejected;
- cross-tenant subscription never readable.

## 21. Compatibility

Stage 12 preserves:

- one User belongs to one Organization;
- tenant derived from authenticated User;
- existing auth status checks;
- four tenant roles;
- temporary-password flow;
- server-side sessions;
- Stage 7 parent billing as a separate domain.