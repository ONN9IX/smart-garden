# Stage 9 — Entrance Kiosk Data, Privacy and 152-FZ Boundary

**Status:** design proposal for Issue #142; frozen only after the design PR merges.
**Owner:** ONN9IX.
**Scope:** technical privacy/security design only.
**Implementation:** NOT AUTHORIZED until Stage 6 integrated acceptance is complete.

## 1. Privacy objective

The entrance tablet is physically exposed and must therefore receive **less data than an ordinary staff workstation**.

Stage 9 minimizes:

- what the kiosk receives;
- what remains visible on screen;
- what can persist on the device;
- what can be inferred from unattended access.

The kiosk is not a general staff portal.

## 2. Data classes

### Allowed kiosk data

Minimal current operational data:

- Group UUID/name;
- Child UUID;
- Child first/last/middle name;
- current-day Attendance status;
- current-day arrival/departure times;
- current garden-local date.

### Explicitly excluded

Do not send to the kiosk:

- Guardian phone/email;
- home address;
- passport or identity-document data;
- contracts;
- charges/payments/debt;
- diary;
- direct/group messages;
- incident descriptions;
- photos;
- photo-consent documents;
- medical/absence reasons;
- birth date by default;
- staff Audit history;
- credentials/secrets.

## 3. Child identity minimization

The kiosk needs enough information for staff to select the correct Child.

Default presentation:

- last name;
- first name;
- middle name where already available.

Do not add birth date, photo, parent name or contact merely for convenience.

If real pilot usability shows duplicate-name ambiguity, the additional disambiguator must be explicitly reviewed before adding it.

## 4. No biometrics

Stage 9 core prohibits:

- face recognition;
- face embeddings;
- fingerprint;
- voiceprint;
- gait recognition;
- biometric identification;
- automated camera classification.

A tablet camera must not silently become a biometric sensor.

Any future biometric idea requires a separate legal, security and privacy decision and is outside this design.

## 5. No public child directory

The kiosk page is authenticated.

There is no anonymous:

- child list;
- child lookup;
- surname autocomplete;
- QR-to-child profile;
- public roster.

All roster requests revalidate role, tenant and Group scope.

## 6. Shared-device threat model

Assume:

- the tablet may be left unattended;
- visitors/parents may physically see the screen;
- the device may be lost/stolen;
- browser storage can survive app restarts;
- a previous staff member may forget to log out.

Therefore Stage 9 requires:

- minimum on-screen PII;
- inactivity logout;
- no persistent business data;
- no shared kiosk password;
- no device-local Attendance authority;
- no offline queue.

## 7. Browser storage

Do not persist to localStorage, sessionStorage, IndexedDB or service-worker caches:

- roster;
- Child names;
- Attendance status/times;
- Group roster payload;
- auth/session material;
- search history.

Transient in-memory React state is allowed only during the active authenticated session.

## 8. HTTP/session security

Reuse the existing HttpOnly session cookie architecture.

Do not introduce:

- bearer token in JavaScript storage;
- kiosk API key in frontend code;
- universal tenant PIN;
- hard-coded staff account.

Production requires HTTPS/TLS under the approved deployment architecture.

## 9. Inactivity logout

The kiosk must actively end the server session after configured inactivity.

Required behavior:

1. clear transient screen state;
2. invoke normal logout;
3. return to Login.

If network prevents logout:

- clear the UI immediately;
- disable kiosk actions;
- require re-authentication once connectivity returns;
- do not reveal the cached roster.

A visual overlay alone is insufficient if it leaves the underlying authenticated kiosk usable.

## 10. Device loss

Because no roster or attendance queue persists locally, a lost powered-off device should not contain a durable kiosk database.

Production operations must still define:

- device passcode;
- OS auto-lock;
- remote wipe where supported;
- browser profile restrictions;
- physical mounting/control;
- update policy.

These are deployment controls, not substitutes for application auth.

## 11. Logs

Allowed technical logs:

- request_id;
- route template;
- method;
- status;
- duration;
- safe actor/org identifiers where needed;
- safe error code.

Avoid logging:

- response roster;
- Child names;
- local search text;
- Attendance payload bodies unless explicitly scrubbed;
- cookies/tokens;
- device identifiers beyond operational necessity.

## 12. Audit

Business Attendance Audit remains authoritative.

Allowed Attendance Audit data is the existing minimized before/after state:

- status;
- arrival time;
- departure time;
- changed fields.

Do not add:

- Child name;
- Group roster snapshot;
- search term;
- Guardian data;
- device fingerprint;
- IP as business detail.

If security operations later require separate kiosk-login telemetry, keep it outside business Audit unless explicitly designed.

## 13. Search privacy

Search should be local in transient memory after an authorized roster fetch.

This prevents sending every entered surname fragment to the server/logs.

Search state disappears on:

- logout;
- inactivity;
- Group switch;
- page reload where appropriate.

## 14. Screen privacy

Kiosk UI should avoid dense lists when not needed.

Recommended:

- show one authorized Group at a time;
- clear search input after successful action if operationally acceptable;
- visually distinguish status without exposing additional child data;
- avoid displaying long historical details.

No dashboard of all children across all Groups is needed.

## 15. Shoulder-surfing mitigation

Application-level minimization should ensure that a person standing near the entrance does not see:

- parent contacts;
- debt/payments;
- diary/incidents;
- medical data;
- photos.

The remaining Child name + attendance state is still personal data and must be protected by operational placement and screen-lock policies.

## 16. Network failure

Network failure must not result in local PII retention for later sync.

No offline queue.

Displayed roster may remain only in current in-memory state until logout/lock, but the UI must clearly indicate that writes are unavailable.

For stricter deployments, implementation may blank the roster after prolonged network loss.

## 17. No browser-authoritative timestamps

Do not trust:

- browser clock;
- browser timezone;
- manually edited client date;
- device local time.

Backend calculates the garden-local date/time.

This reduces manipulation and incorrect Attendance data on misconfigured shared devices.

## 18. Parent pickup identity

Stage 9 core does not store who picked up the Child.

No new:

- authorized-person registry;
- passport fields;
- pickup-person photo;
- signature image;
- identity scan.

A future pickup-authorization module requires a separate privacy/legal design.

## 19. QR/NFC boundary

No permanent QR/NFC credential is part of Stage 9 core.

Future tokenized self-service must address:

- theft/copy/replay;
- expiry/rotation;
- Guardian authorization;
- revocation;
- device binding if any;
- logs;
- emergency fallback.

Do not encode raw Child/Guardian UUIDs as standalone access credentials.

## 20. Physical access-control boundary

Attendance write does not imply:

- a door opened;
- an adult was identity-verified;
- custody transfer was legally validated.

A future physical-access system needs its own event model and threat model.

Do not use Attendance timestamps as security proof beyond their defined operational meaning.

## 21. Dev/test/preview

Synthetic-only:

- Groups;
- Child names;
- Attendance;
- staff users.

Do not use:

- real kindergarten roster;
- production screenshots;
- real parent names/contacts;
- production database copies.

Synthetic names should be clearly fictional/test-oriented.

## 22. Third-party analytics

Do not send kiosk PII to third-party:

- session replay;
- analytics;
- crash capture containing payloads;
- AI;
- marketing SDKs.

Any future telemetry provider requires explicit data-flow/privacy review.

## 23. Retention

Stage 9 creates no new business-data retention category if it uses canonical Attendance only.

Existing Attendance/Audit retention decisions remain applicable.

Kiosk-specific technical logs should follow the future production logging-retention policy and should not become a second personal-data archive.

## 24. 152-FZ deployment boundary

Before a real pilot, separately determine:

- legal basis for Child Attendance processing;
- operator/processor roles;
- hosting/data localization;
- staff access administration;
- device access policy;
- physical tablet placement;
- incident response for lost/stolen device;
- log retention;
- backup protection;
- subject-access/deletion obligations where applicable.

Technical controls alone do not establish full legal compliance.

## 25. Required privacy tests

Future Stage 9 implementation must verify:

1. PARENT cannot access kiosk.
2. TEACHER cannot see unassigned Group.
3. foreign-tenant Group/Child hidden.
4. roster response contains no Guardian contacts.
5. roster response contains no finance/diary/messages/photos.
6. no client-provided date/time accepted.
7. browser persistent storage has no roster/Attendance payload.
8. logout/inactivity clears the visible roster.
9. no offline queue is created.
10. Audit details contain no Child names/search terms.
11. technical logs do not print request/response roster bodies.
12. synthetic-only fixtures are used.

## 26. Acceptance boundary

A green Stage 9 technical acceptance proves:

- the kiosk is narrow;
- role/tenant/assignment boundaries are enforced;
- canonical Attendance is reused;
- device-local persistence is minimized;
- online failure is fail-closed.

It does not prove:

- full 152-FZ compliance;
- physical access-control certification;
- custody-transfer verification;
- authorization for biometric processing;
- readiness for an unattended public terminal.