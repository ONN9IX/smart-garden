# Stage 8 — PARENT Data, Privacy and 152-FZ Boundary

**Status:** design proposal for Issue #139; frozen only after the design PR merges.
**Owner:** ONN9IX.
**Scope:** technical privacy design only.
**Implementation:** NOT AUTHORIZED until Stage 6 integrated acceptance is complete.

## 1. Privacy objective

The PARENT cabinet exposes only the minimum child/family information required for the authenticated Guardian to use Smart Garden.

The cabinet must not become a broad family profile, medical record, guardian directory or financial disclosure surface.

## 2. Eligibility classes

### Ordinary child entitlement

Derived from:

- authenticated PARENT User;
- same-tenant Guardian mapping;
- active ChildGuardian relation;
- active/eligible Child context.

Used for:

- child overview;
- attendance read;
- schedule;
- announcements;
- group/direct communication;
- diary;
- polls;
- photos;
- ordinary parent notifications/notices.

### Financial entitlement

Stricter and controlled by Stage 7:

- ordinary child entitlement is necessary but insufficient;
- Guardian must also be the Contract's `contracting_guardian_id`.

Stage 8 must not merge these eligibility models.

## 3. Minimal child data

Use already-authorized Child fields only.

Do not add:

- passport/identity data;
- insurance data;
- diagnosis;
- medication;
- allergies/medical notes;
- biometric templates;
- face recognition identifiers;
- unrestricted free-form parent notes.

Any future health/safety requirement requires a separate legal/privacy design.

## 4. Attendance privacy

PARENT attendance view may include:

- date;
- present/absent status;
- arrival;
- departure;
- safe historical Group presentation where needed.

It must not include:

- diagnosis;
- absence reason;
- medical certificate content;
- another Child's attendance;
- teacher/internal operational notes.

Attendance is not copied into third-party analytics or persistent browser storage.

## 5. Schedule privacy

Schedule is ordinary operational information.

PARENT receives only the schedule relevant to the currently eligible Child/Group.

Do not return internal management metadata, creator identifiers or another Group's schedule unless independently eligible.

## 6. Communication privacy

### Group thread

The PARENT may see the minimum sender presentation needed for conversation context.

Do not expose a complete parent/guardian directory, contact export or participant list merely because users share a Group.

### Direct thread

Only current eligible participants may read content.

DIRECTOR/ADMIN do not receive blanket direct-message access.

Message body is excluded from:

- technical logs;
- Audit.details;
- Today payload;
- notification body duplication;
- analytics.

## 7. Diary privacy

Diary content can contain contextual child information and is treated as sensitive business free text.

Rules:

- linked Child only;
- no Home free-text duplication;
- no logs/Audit.details;
- no browser persistent storage;
- no search-engine/public indexing;
- no cross-child caching.

Stage 8 does not add medical diary fields.

## 8. Announcement privacy

Eligible announcement content can be displayed normally to authorized PARENT users.

Do not place other audience membership data, Guardian contacts or unnecessary author PII into the response.

## 9. Poll privacy

Store/use only what the frozen poll contract requires.

PARENT must not receive:

- another PARENT's individual vote identity unless explicitly frozen elsewhere;
- another Group's poll;
- a participant roster from poll results.

Aggregates are preferred.

## 10. Photo privacy

Stage 6 remains authoritative.

Requirements:

- no public URL;
- authenticated delivery;
- consent gate;
- active relation/eligibility;
- no facial recognition;
- no biometric processing;
- no automatic child identification;
- synthetic photos in dev/test/preview;
- bytes/object secrets not logged;
- PARENT Today receives only safe count/state, not bytes.

## 11. Document Notice privacy

PARENT notices are metadata-only.

Allowed:

- title;
- kind;
- issued_at;
- requires_ack;
- acknowledged_at;
- safe target/reference if needed.

Do not put into notice payload:

- passport scan;
- signed contract bytes;
- arbitrary private document;
- another recipient's data.

Binary document delivery requires the separate protected-document architecture.

## 12. Stage 7 financial privacy

Stage 8 must render Stage 7 finance only after Stage 7 authorization succeeds.

Never infer financial entitlement from:

- selected child alone;
- same surname;
- same Group;
- another Guardian relation;
- cached previous response.

Do not show another Guardian's:

- contract number;
- balance;
- debt;
- payment history;
- receipt.

## 13. Today/Home minimization

Home is a summary surface and therefore has stricter minimization.

Allowed examples:

- attendance status;
- schedule item title/time;
- unread counts;
- “new diary entry” indicator;
- poll action count;
- photo availability count;
- notice-ack count;
- Stage 7 amount/status only for entitled financial context.

Forbidden:

- message body;
- diary body;
- photo bytes;
- direct-thread preview containing sensitive text;
- incident details;
- medical data;
- another Guardian's financial information;
- contract/receipt body.

## 14. Multi-child isolation

Switching Child A → Child B must:

- refetch/re-authorize B data;
- not reuse A's cached payload as B content;
- clear transient child-specific state where appropriate;
- preserve only non-sensitive UI preference state.

Backend responses must remain independently authorized even if frontend state is stale.

## 15. Browser storage

Do not persist sensitive PARENT payloads in:

- `localStorage`;
- `sessionStorage`;
- long-lived IndexedDB;
- offline caches not explicitly privacy-reviewed.

This includes:

- Child PII;
- attendance;
- messages;
- diary;
- photo metadata/content;
- document notices;
- finance;
- receipts.

Session/auth remains the existing HttpOnly-cookie architecture.

## 16. Technical logging

Allowed minimum:

- request_id;
- method;
- path template;
- status;
- duration;
- safe actor/org IDs when necessary;
- safe error code.

Never log:

- full PARENT request/response payloads;
- message body;
- diary body;
- child names unnecessarily;
- phone/email;
- photo bytes/object keys;
- contract/receipt content;
- payment data beyond approved safe IDs;
- auth cookies/tokens.

## 17. Audit

Stage 8 ordinary PARENT reads do not require copying sensitive content into Audit.

Where actions are audited, use:

- actor UUID;
- target type/UUID;
- state transition;
- changed field name;
- safe action enum.

Never put in Audit.details:

- message body;
- diary text;
- photo bytes;
- Guardian contact fields unless explicitly necessary;
- financial secrets;
- document content.

## 18. Notifications

Notifications must be minimal.

Preferred wording:

- “Новое объявление”
- “Новое сообщение”
- “Обновлён дневник”
- “Доступен новый опрос”
- “Доступно новое фото”
- “Есть уведомление, требующее подтверждения”

Do not include message/diary content or sensitive child/financial details in push/email/SMS payloads without a separate external-channel privacy review.

## 19. External services

Do not send PARENT cabinet PII to external:

- analytics;
- session replay;
- AI;
- crash/error systems with payload capture;
- messaging providers;
- photo/file providers

without an explicit data-flow/privacy decision.

## 20. Dev/test/preview

Synthetic data only.

Do not use:

- real Child/Guardian names;
- real phone/email;
- real conversations;
- real diary entries;
- real photos;
- real attendance;
- real contracts/payments/receipts;
- production DB copies.

## 21. Retention

Stage 8 does not invent retention periods.

Existing/future retention decisions must cover:

- Child/Guardian relationship;
- attendance;
- messages;
- diary;
- poll votes;
- photos;
- notifications;
- document notices;
- Stage 7 finance;
- backups.

Loss of current UI eligibility does not automatically mean physical deletion.

## 22. Data export / subject requests

A future subject-access/export process must preserve:

- another Guardian's privacy;
- other children/participants' privacy;
- direct-thread participant boundaries;
- Stage 7 financial entitlement;
- protected-photo/document controls.

Stage 8 does not create a bulk family export endpoint.

## 23. Required privacy negative tests

Future implementation must verify:

1. foreign tenant Child hidden;
2. same-tenant unlinked Child hidden;
3. inactive relation revokes access;
4. Child A data does not leak after switching to Child B;
5. no other Guardian directory/contact data is exposed;
6. direct-message non-participant denied;
7. message/diary sentinel absent from logs/Audit/Today;
8. no medical fields in Attendance/Diary additions;
9. photo content has no public URL;
10. consent withdrawal blocks ordinary photo read;
11. another User's Notification/Notice denied;
12. browser persistent storage remains free of sensitive PARENT payload;
13. financial surface denied to non-contracting Guardian;
14. no real PII fixtures;
15. safe errors do not reveal hidden resource existence.

## 24. Pre-pilot boundary

Before real data/pilot, independently resolve:

- legal basis for Parent/Child processing;
- operator/processor roles;
- hosting/data localization;
- subprocessors;
- retention/destruction;
- backup protection;
- access administration/revocation;
- photo consent legal source/evidence;
- external messaging/photo/document providers;
- Stage 7 financial/legal obligations;
- incident/breach process;
- Roskomnadzor obligations where applicable.

## 25. Acceptance boundary

A green Stage 8 technical acceptance proves only that software follows the frozen technical privacy contract.

It does not by itself prove full 152-FZ compliance or authorize production processing of real family data.