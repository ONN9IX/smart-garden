# Stage 12 — Tenant Onboarding Data, Privacy and 152-FZ Boundary

**Status:** design proposal for Issue #148; frozen only after the design PR merges.
**Owner:** ONN9IX.
**Scope:** technical privacy/security design only.
**Implementation:** NOT AUTHORIZED until Stage 6 integrated acceptance is complete.

## 1. Data minimization objective

Stage 12 should create a usable kindergarten tenant with the least possible personal/commercial data.

Core provisioning requires only:

- Organization name;
- timezone;
- initial DIRECTOR username;
- temporary password delivered securely and stored only as a hash;
- subscription plan/status/period metadata.

Do not add speculative legal/company identity fields until a concrete operational/legal requirement exists.

## 2. Initial DIRECTOR data

The first DIRECTOR account is personal/account data.

Minimize to existing User fields.

Do not add by default:

- passport data;
- personal phone;
- personal email;
- home address;
- birth date;
- payment card;
- bank account.

If future onboarding requires an email/phone for recovery or business contact, add it through a separate explicit account/contact design.

## 3. Organization data

Organization core remains:

- name;
- status;
- timezone;
- timestamps.

Do not overload Organization with commercial secrets or legal-document scans.

Subscription metadata belongs in a separate entity.

## 4. Subscription privacy

Commercial subscription data is visible only where needed.

DIRECTOR read-only access is sufficient in core.

TEACHER/PARENT do not need to know:

- plan price;
- overdue state;
- commercial period;
- external account reference.

ADMIN access may remain absent unless future operations prove necessity.

## 5. No payment credentials

Stage 12 core never stores:

- PAN/card number;
- CVV;
- acquiring secret;
- bank login;
- banking password;
- payment token;
- provider API secret.

Real SaaS payment integration is separate.

## 6. Temporary password handling

Plaintext temporary password must exist only transiently during secure provisioning/delivery.

It must never be:

- logged;
- returned in repeated status calls;
- stored in Audit;
- stored in subscription metadata;
- committed to repository;
- included in screenshots.

Database stores password hash only.

## 7. Provisioning logs

Allowed:

- provisioning request/reference ID;
- Organization UUID;
- User UUID;
- plan code;
- success/failure;
- safe error code;
- timing.

Avoid:

- plaintext password;
- full request body;
- unnecessary username repetition;
- external billing secrets.

## 8. Audit

Business/operations Audit may record:

- tenant provisioned;
- subscription state change;
- Organization blocked/archived.

Do not include:

- password/hash;
- secret token;
- payment credential;
- full commercial contract;
- arbitrary operator free text with PII.

Use bounded reason/status codes where possible.

## 9. No public self-signup in core

Because Stage 12 has no anonymous self-service tenant creation, it avoids collecting public signup PII before the operator has approved the tenant.

A future public trial signup requires:

- anti-abuse;
- contact verification;
- privacy notice;
- rate limits;
- account recovery;
- consent/legal review.

That is a separate gate.

## 10. No cross-tenant operator shortcut in tenant app

Do not create a tenant User who can switch Organization context.

The tenant app remains one authenticated User → one Organization.

Any future platform operator UI must use a separate security boundary.

## 11. Access blocking and personal data

Organization.status=blocked denies tenant access under current auth behavior.

Because this affects access to personal data and operational records, blocking must remain explicit and auditable.

Do not let an automated invoice job silently revoke all access.

## 12. Cancellation and retention

Subscription cancellation is a commercial event, not a data-destruction event.

Do not automatically delete:

- Organization;
- Users;
- Child/Guardian records;
- documents;
- Audit;
- backups.

Retention/destruction requires an approved policy.

## 13. Offboarding export

Before a real pilot, define what the kindergarten may need to export at offboarding and who is authorized to request it.

Stage 12 core does not expose a bulk export endpoint.

Future export must preserve:

- tenant authorization;
- other parties' privacy;
- protected-document rules;
- Audit/security data boundaries.

## 14. Archived tenant

Organization archived means the tenant is no longer active in the application.

It does not prove physical deletion.

A later destruction process must address:

- primary DB;
- protected-object storage;
- backups;
- logs;
- provider systems.

## 15. Dev/test/preview

Synthetic-only:

- organization names;
- usernames;
- subscriptions;
- commercial references.

Do not use:

- real customer database copies;
- real contract/invoice references;
- real administrator credentials.

## 16. Commercial analytics

Do not send tenant commercial status to third-party analytics by default.

If business analytics is later needed, use minimized organization/subscription identifiers and review provider/data flow.

Never include Child/Parent data in SaaS subscription analytics.

## 17. Support access

Support should troubleshoot subscription using:

- Organization UUID;
- subscription UUID;
- safe plan/status;
- request IDs.

Do not request passwords from tenant users.

Any privileged support access to tenant business data requires a separate operational access policy.

## 18. Subscription notices

If the product displays notices such as trial ending or payment overdue:

- show them to DIRECTOR only in core;
- avoid exposing commercial status on teacher/parent screens;
- do not put unnecessary commercial details in external push/SMS/email until those channels are privacy-reviewed.

## 19. External billing provider boundary

Before connecting a SaaS billing/payment provider, review:

- provider;
- data region;
- merchant/customer identifiers;
- payment/fiscal responsibilities;
- webhook secrets;
- retention;
- subprocessors.

Provider-specific data is not part of Stage 12 core.

## 20. Subject/personal data boundary

Stage 12 creates almost no new personal data beyond the existing DIRECTOR User.

The broader 152-FZ obligations of Smart Garden still apply to the tenant's Child/Guardian/staff data, but those are governed by their respective stages and pre-pilot legal review.

## 21. Required privacy tests

Future implementation must verify:

1. plaintext temporary password absent from logs/Audit/database.
2. TEACHER/PARENT cannot read subscription.
3. cross-tenant subscription hidden.
4. no card/bank credential fields exist.
5. past_due does not mutate Organization.status.
6. cancelled does not delete/archive tenant automatically.
7. provisioning fixtures are synthetic.
8. safe errors do not expose secrets.
9. browser persistent storage does not contain commercial secrets.
10. no global tenant-switching capability is introduced for tenant Users.

## 22. Pre-pilot decisions

Before real customer onboarding:

- commercial contract/process;
- responsible platform operator access;
- secure temporary credential delivery;
- account recovery procedure;
- retention/offboarding;
- support/admin access;
- subscription invoice/payment process;
- provider choice if automated billing is introduced;
- legal/privacy documentation.

## 23. Acceptance boundary

Technical Stage 12 acceptance proves tenant provisioning and subscription state separation are implemented safely.

It does not itself authorize real customer contracting, determine tax/fiscal obligations, or prove full 152-FZ compliance.