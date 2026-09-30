# Stage 8 — PARENT Permissions and API

**Status:** design proposal for Issue #139; frozen only after the design PR merges.
**Owner:** ONN9IX.
**Implementation:** NOT AUTHORIZED until Stage 6 integrated acceptance is complete.
**Conventions:** `/api/v1`, JSON `snake_case`, UUID identifiers, server-owned tenant/actor fields.

## 1. Authorization invariants

1. Authenticated User is the only source of actor, role and tenant.
2. PARENT access to a Child requires an active same-tenant ChildGuardian relation.
3. Financial access is not inherited from ordinary Child visibility; Stage 7 contracting-Guardian rules remain authoritative.
4. Client-supplied `organization_id`, `guardian_id`, actor, sender or participant never grants authority.
5. Hidden/cross-tenant objects use the active non-disclosure behavior.
6. Frontend navigation is not authorization.
7. Relation changes take effect on the next backend request.

## 2. Capability matrix

| Capability | DIRECTOR | ADMIN | TEACHER | PARENT |
|---|---|---|---|---|
| PARENT Today | N/A | N/A | N/A | own eligible context |
| Read linked children | management rules | management rules | assigned roster only | linked only |
| Read child Attendance | all | all | assigned groups | linked child only |
| Write Attendance | all | all | assigned groups | NO |
| Read child Schedule | all | all | assigned groups | linked current group only |
| Announcements | manage | manage | frozen Stage 6 teacher scope | eligible read |
| Group communication | frozen management group scope | frozen management group scope | assigned group | eligible group |
| Direct TEACHER↔PARENT | no blanket content | no blanket content | participant only | participant only |
| Diary | management read | operational read | assigned child read/write | linked child read |
| Poll vote | NO | NO | NO | eligible poll only |
| Photos | admin oversight | frozen operational scope | assigned + consent | linked + consent |
| Own Notifications | own | own | own | own |
| Own Document Notices | issue/list under frozen rules | issue/list under frozen rules | own/ack | own/ack when enabled |
| Stage 7 finance | management rules | management rules | NO | contracting Guardian only |

## 3. Parent context API

Proposed Stage 8 aggregation routes:

- `GET /api/v1/parent/today?child_id=`
- `GET /api/v1/parent/children`
- `GET /api/v1/parent/children/{child_id}`

`child_id` is an object selector only. Backend revalidates the active Guardian relation and tenant.

### `GET /parent/children`

Return minimal eligible children:

- id;
- name presentation using already authorized fields;
- current active Group minimal presentation if available;
- relation/eligibility state needed by UI.

Do not return another Guardian list, finances or unrelated group data.

### `GET /parent/today`

For one selected eligible Child, may aggregate:

- garden-local date;
- attendance status/times;
- today's schedule;
- unread eligible announcement count;
- unread communication count;
- diary update indicator;
- active poll action count;
- photo availability count/indicator;
- own unread notification count;
- own notice-ack count;
- Stage 7 financial attention only after Stage 7 exists and entitlement passes.

Do not embed message/diary body or photo/document content.

## 4. Attendance API

Proposed read-only route:

- `GET /api/v1/parent/children/{child_id}/attendance?date_from=&date_to=`

Response is minimized:

- attendance id;
- date;
- status;
- arrival_at;
- departure_at;
- historical group id/name only where required for presentation.

Forbidden in Stage 8:

- POST/PATCH PARENT attendance;
- absence reason;
- diagnosis;
- medical free text;
- arbitrary Group/Child selector bypass.

## 5. Schedule API

Proposed:

- `GET /api/v1/parent/children/{child_id}/schedule`

Backend resolves the Child's eligible current Group.

The client does not gain authority by sending a Group ID.

Response:

- schedule item id;
- weekday/date context;
- start_time;
- end_time;
- title.

No management fields unnecessary to the PARENT experience.

## 6. Announcements

Use the Stage 6 PARENT announcement contract.

Preferred PARENT routes remain under the existing/frozen PARENT namespace established by Stage 6 implementation.

Stage 8 may aggregate counts/links but must not create a duplicate announcement model or conflicting route family.

Eligibility:

- active all-garden announcements;
- active current eligible Group announcements.

Deduplication is server-side.

## 7. Communication

Stage 8 reuses Stage 6 routes/semantics.

No new participant model.

For every thread/message request:

- actor comes from authenticated PARENT;
- tenant is server-owned;
- group/child/guardian relation is revalidated;
- direct thread participant scope is enforced;
- sender is server-owned.

A PARENT payload never supplies an authoritative participant list.

## 8. Diary

Reuse:

- `GET /api/v1/parent/children/{child_id}/diary`

No PARENT write route is added.

If Stage 8 adds a Home indicator, it should carry only metadata such as unread/new state or latest date, not diary free text.

## 9. Polls

Reuse the Stage 6 PARENT poll routes once implemented.

Required semantics remain:

- active eligible Group only;
- one vote per eligible PARENT under frozen rules;
- option belongs to Poll;
- no actor spoofing;
- no cross-group vote.

Stage 8 only integrates the surface into coherent navigation/Home.

## 10. Photos

Reuse Stage 6 PARENT photo API once implemented.

Content route must revalidate:

- active relation;
- tenant;
- child/asset eligibility;
- active consent requirements.

No public URL.

The Today aggregator may return only safe counts/metadata.

## 11. Notifications

Reuse existing Notification.

PARENT routes:

- list own;
- read own;
- mark own read.

No recipient selector controlled by client.

Notification entity references are checked again when opening the destination.

## 12. Document Notices

Stage 8 freezes a PARENT recipient surface only if compatible with the Stage 6 model.

Proposed routes:

- `GET /api/v1/parent/document-notices`
- `GET /api/v1/parent/document-notices/{notice_id}`
- `POST /api/v1/parent/document-notices/{notice_id}/acknowledge`

Rules:

- recipient is authenticated User;
- client cannot choose recipient;
- immutable metadata-only notice;
- acknowledgement is idempotent;
- no binary attachment/file URL.

If current Foundation recipient constraints cannot support PARENT without a shared schema/migration change, implementation must STOP and serialize that dependency rather than weakening the model.

## 13. Stage 7 financial routes

Do not duplicate or rename the frozen Stage 7 API.

Stage 8 consumes, when implemented:

- `GET /api/v1/parent/contracts`
- `GET /api/v1/parent/contracts/{contract_id}`
- Stage 7 acknowledgement/document routes;
- `GET /api/v1/parent/billing/summary`
- Stage 7 charges/payments/receipts routes.

The Stage 7 contracting-Guardian authorization function remains authoritative.

## 14. Child selector semantics

The UI can retain a currently selected `child_id` for the active view, but the server never treats it as proof of authorization.

If the selected relation is removed:

- next request denies/hides the child;
- UI removes that Child from selector after refresh;
- no stale child-specific payload is reused for another child.

## 15. Response minimization

### Child list

Return only fields needed to identify/select the Child and current context.

### Today

Return counts/statuses and safe references.

Do not return:

- message body;
- diary text;
- contract body;
- payment references unless Stage 7 screen specifically requires them;
- photo bytes;
- another Guardian's data;
- incident details.

### Attendance

Return status/times only; no medical context.

## 16. Errors

Use current structured API error envelope.

Expected:

- unauthenticated → auth error;
- wrong role → 403;
- unlinked/foreign Child → hidden-resource behavior;
- inaccessible thread/photo/poll/notice → hidden-resource behavior;
- invalid date/filter → validation error;
- unavailable Stage 7 module → safe feature/unavailable behavior, not data leakage.

Never expose SQL, traceback, object-storage key, another Guardian identity or cross-tenant existence.

## 17. URL rules

Allowed:

- UUID;
- date;
- enum;
- pagination.

Do not put in URLs:

- child/parent names;
- phone/email;
- message body;
- diary text;
- contract text;
- payment secret/reference unless specifically designed and safe;
- photo/document storage identifiers.

## 18. Browser storage

Do not persist PARENT business payloads in `localStorage`, `sessionStorage` or long-lived IndexedDB.

In particular:

- messages;
- diary entries;
- attendance history;
- child PII;
- photos;
- document content;
- contract/payment/receipt data.

HttpOnly session cookie remains authoritative.

## 19. Required negative tests

### Tenant / relation

- foreign Child hidden;
- same-tenant but unlinked Child hidden;
- archived/inactive relation loses access;
- sibling or another linked Child does not authorize selected-child resources;
- client organization_id ignored/rejected.

### Attendance / schedule

- PARENT write Attendance denied;
- another Child Attendance denied;
- forged Group selector does not grant schedule access;
- no medical/absence-reason field appears.

### Communication

- direct thread non-participant denied;
- group relation change removes eligibility;
- sender/participant spoofing rejected.

### Diary / polls / photos

- unlinked diary denied;
- cross-group poll vote denied;
- duplicate vote rejected;
- consent-withdrawn photo read denied;
- no public photo URL.

### Notifications / notices

- another User notification denied;
- another User notice denied;
- recipient spoofing rejected;
- duplicate acknowledgement idempotent.

### Finance

- non-contracting Guardian denied Stage 7 finance;
- ordinary Child relation does not grant finance;
- TEACHER denied Stage 7 finance remains green.

## 20. Required browser flow

```text
PARENT login
→ Home
→ select Child A
→ Attendance
→ Schedule
→ Announcements
→ Group communication
→ Direct Teacher communication
→ Diary
→ Poll
→ Photos
→ Notifications
→ Document Notice acknowledgement
→ switch Child B
→ verify no Child A data leaks
→ Stage 7 finance only when entitled
→ logout
```

## 21. Compatibility

No route in Stage 8 may:

- redesign Stage 6 TEACHER participant rules;
- grant management permissions to PARENT;
- widen DIRECTOR/ADMIN direct-message access;
- weaken photo consent;
- change Stage 7 financial entitlement;
- create another auth/tenant mechanism.