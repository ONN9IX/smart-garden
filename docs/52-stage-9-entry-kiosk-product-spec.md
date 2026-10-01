# Stage 9 — Entrance Tablet / Attendance Kiosk Product Specification

**Status:** design proposal for Issue #142; frozen only after the design PR merges.
**Owner:** ONN9IX.
**Implementation:** NOT AUTHORIZED until Stage 6 integrated acceptance is complete.
**Design baseline:** `4993d3e1f3128b8a1f23c7d7c085084b062fc6b8`.

## 1. Goal

Provide a fast entrance-tablet workflow for staff without creating a second attendance system or a physical access-control system.

The Stage 9 core flow is:

```text
authenticated staff
→ kiosk mode
→ authorized Group
→ minimal Child roster
→ Arrival / Departure
→ canonical Attendance record
→ privacy-safe Audit
→ existing management/teacher/parent views observe the same data
```

The entrance tablet is an operational UI over the existing Attendance domain.

## 2. What Stage 9 core is

Stage 9 core is:

- a touch-first entrance screen;
- a narrow server adapter over canonical Attendance;
- current-day arrival/departure marking;
- role/tenant/assignment-aware;
- online-only;
- fail-closed;
- synthetic-data compatible;
- usable on a fixed tablet or ordinary browser.

## 3. What Stage 9 core is not

Stage 9 core is not:

- a turnstile controller;
- a smart-lock controller;
- an intercom;
- a visitor-management platform;
- a parent self-check-in terminal;
- a biometric system;
- a face-recognition system;
- an NFC/QR credential system;
- an offline attendance database.

Those capabilities require separate future design gates.

## 4. Canonical Attendance rule

There is exactly one attendance source of truth: the existing `Attendance` model/service.

Stage 9 does not introduce:

- `EntryAttendance`;
- a kiosk-specific attendance table;
- a shadow local attendance database;
- a second daily status.

Kiosk actions produce or update the same canonical Attendance record already used by DIRECTOR/ADMIN and TEACHER attendance screens.

The existing uniqueness semantics of one Attendance record per Child/date remain authoritative.

## 5. Roles

### DIRECTOR

May enter kiosk mode and use it for any active same-tenant Group.

### ADMIN

May enter kiosk mode and use it for any active same-tenant Group.

### TEACHER

May enter kiosk mode only for currently assigned active Groups under existing Stage 6 assignment rules.

If Employee, Group or assignment becomes inactive, the next request loses kiosk access.

### PARENT

No Stage 9 kiosk write access.

PARENT self-check-in is explicitly deferred because it requires a separate identity/pickup/security design.

## 6. Kiosk session

Stage 9 core reuses existing authenticated staff sessions.

It does not create:

- a kiosk superuser;
- a shared universal PIN;
- a permanent device password;
- a browser-stored auth token.

Recommended operational flow:

```text
staff login
→ open Kiosk
→ perform entrance work
→ inactivity timeout
→ logout
→ next staff member authenticates again
```

Kiosk UI should trigger normal server logout after the configured kiosk inactivity period and clear all transient roster state.

A future dedicated device-enrollment/session architecture is a separate gate.

## 7. Kiosk Home

Show only:

- current garden-local date;
- current authenticated role/user presentation;
- authorized active Groups;
- connection/backend state;
- logout.

Do not show:

- global parent directory;
- Guardian phone/email;
- contracts/payments;
- diary/messages;
- incidents;
- photos;
- medical information.

## 8. Group roster

After selecting an authorized Group, show minimal active Child presentation:

- Child UUID internally;
- first name;
- last name;
- middle name if already part of normal presentation;
- current-day attendance state;
- arrival time if present;
- departure time if present.

No birth date is required for the core kiosk unless a later usability review proves ambiguity cannot be resolved safely without it.

No Guardian data appears on the kiosk roster.

## 9. Search

Search is permitted only inside the currently authorized roster.

Search input may match the minimal displayed Child name.

The server remains authoritative for Group and Child eligibility.

The kiosk must not expose a tenant-wide anonymous child-search endpoint.

## 10. Arrival action

Arrival is available for an active Child in an authorized active Group for **garden-local today only**.

The server, not the browser, determines:

- current garden-local date;
- current garden-local wall time.

Arrival semantics:

### No Attendance record / unknown

Create/upsert:

- status = `present`;
- arrival_time = server garden-local current time;
- departure_time = null.

### Existing absent

Change to:

- status = `present`;
- arrival_time = server garden-local current time;
- departure_time = null.

This is a business correction caused by actual arrival and remains Audit-visible.

### Existing present without arrival

Set arrival_time to server garden-local current time.

### Existing present with arrival and without departure

Repeated Arrival is idempotent:

- return current canonical Attendance;
- do not create a second record;
- do not change arrival_time;
- do not create duplicate business Audit merely because the client retried.

### Existing present with departure

Arrival button is not a silent “second visit” operation.

Stage 9 core does not support multiple arrival/departure cycles in one day because canonical Attendance currently contains only one arrival and one departure.

Return a safe conflict such as `ATTENDANCE_ALREADY_DEPARTED` and direct staff to the standard Attendance correction workflow.

## 11. Departure action

Departure is available for garden-local today only.

### No Attendance / unknown

Reject with a stable business conflict such as:

`ARRIVAL_REQUIRED`

### Absent

Reject with `ARRIVAL_REQUIRED`.

### Present without arrival

Reject and require normal Attendance correction. Stage 9 must not invent an arrival time.

### Present with arrival and no departure

Set departure_time to server garden-local current time.

### Present with departure

Repeated Departure is idempotent:

- return current Attendance;
- preserve the first confirmed departure time;
- no duplicate Audit event for a pure retry.

## 12. No multi-entry model in Stage 9 core

The current Attendance model is daily summary state, not an immutable turnstile event ledger.

Therefore Stage 9 core supports one arrival and one departure per Child/day.

Use cases such as:

- left for appointment and returned;
- multiple pickups/returns;
- detailed doorway event history;

require a future `AccessEvent` design and likely migration. They must not be simulated by overwriting timestamps silently.

## 13. Corrections

The kiosk is optimized for fast current-day operation.

It does not provide arbitrary editing of:

- date;
- status;
- arrival time;
- departure time.

Corrections use the existing authorized Attendance screens/APIs.

This avoids turning the entrance tablet into a broad historical-management surface.

Every correction remains subject to existing role rules and Audit.

## 14. Absent status

The kiosk does not need a fast “Absent” action.

Absence is managed in the existing Attendance workflow.

Rationale:

- arrival/departure is what the entrance tablet actually observes;
- an unarrived child remains `unknown` until staff explicitly records absence elsewhere;
- kiosk must not guess absence based on time.

## 15. Garden-local date/time

Stage 9 reuses `Organization.timezone`.

Server-side kiosk actions calculate:

- `organization_today(actor.organization)`;
- current local wall time in the same validated IANA timezone.

The client clock is never authoritative for attendance writes.

A browser with the wrong timezone must not change the saved date/time.

## 16. Current-day only rule

Kiosk write routes operate only on organization-local today.

No client date parameter is accepted for Arrival/Departure.

This makes the shared entrance tablet narrow and reduces accidental historical edits.

Historical correction remains in standard Attendance.

## 17. Network behavior

Stage 9 core is online-only and fail-closed.

If Backend is unavailable:

- no local success state;
- no offline mutation queue;
- no IndexedDB/localStorage attendance queue;
- show explicit “Нет связи — отметка не сохранена” state;
- allow safe Retry;
- staff follows the kindergarten's fallback procedure and later uses normal correction if needed.

## 18. Success behavior

The UI may show success only after a successful server response.

No optimistic “Пришёл/Ушёл” state before persistence.

After success:

- update the row from returned canonical Attendance;
- show the server-confirmed time;
- briefly show an accessible confirmation.

## 19. Touch-first UX

Requirements:

- large tap targets;
- simple Group selector;
- fast local roster filtering;
- clear status labels;
- high-contrast Arrival/Departure actions;
- minimal scrolling;
- responsive portrait/landscape tablet layout;
- explicit loading/saving state;
- accidental double-tap safe through idempotency;
- no modal chain for routine valid actions.

A confirmation may be used for Departure if usability testing shows accidental taps are common, but the server idempotency rule remains mandatory.

## 20. Status presentation

Suggested safe states:

- `Не отмечен` — no record / unknown;
- `Отсутствует` — explicit absent;
- `Пришёл HH:MM`;
- `Ушёл HH:MM`.

The UI must not infer “absent” from “not arrived”.

## 21. Shared tablet privacy

The entrance tablet is physically visible and therefore receives stricter presentation minimization.

Do not show:

- Guardian contact information;
- home address;
- contract/billing;
- payment debt;
- diary;
- messages;
- photos;
- incident descriptions;
- medical data;
- birth date unless separately justified.

Only the authorized active roster for the selected Group is displayed.

## 22. Inactivity and unattended device

Core design requires:

- configurable kiosk UI inactivity period;
- automatic invocation of normal logout;
- clearing in-memory roster/search state;
- return to Login screen.

Exact timeout value is an implementation/operations setting and must be chosen during Stage 9 implementation preflight.

Browser/device OS kiosk mode and screen-lock policy are deployment controls, not application auth replacements.

## 23. Audit

The canonical Attendance Audit remains the business audit source.

Kiosk actions must produce the same privacy-minimized attendance create/update audit semantics for real state changes.

A pure idempotent retry that changes nothing does not need a duplicate business audit event.

Do not log:

- search text unnecessarily;
- full roster payload;
- child names in Audit.details;
- browser/device fingerprint.

## 24. PARENT visibility

Stage 9 does not create new PARENT attendance permissions.

When Stage 8 PARENT attendance is implemented, it reads the same canonical Attendance and will naturally reflect kiosk writes.

No separate synchronization is needed.

## 25. Notifications

Automatic “Child arrived/departed” parent notifications are not part of Stage 9 core.

They may be added later only after:

- notification UX decision;
- duplicate/noise controls;
- external-channel privacy review if push/SMS/email is used.

## 26. Physical door integration boundary

No Stage 9 core endpoint opens a door or turnstile.

A future physical access-control integration must separately define:

- device identity/enrollment;
- command authentication;
- fail-safe/fail-secure behavior;
- anti-replay;
- network topology;
- emergency override;
- event ledger;
- physical safety;
- vendor;
- secrets;
- incident handling.

Attendance must not be treated as proof that a physical door command succeeded.

## 27. Parent/guardian pickup identity boundary

Stage 9 core records Child arrival/departure only.

It does not assert **who** dropped off or collected the Child.

If the product later needs pickup authorization, it requires a separate design for:

- authorized persons;
- identity verification;
- revocation;
- emergency exceptions;
- minimum PII;
- audit/retention.

Do not add passport or identity-document fields to Stage 9 core.

## 28. Product acceptance target

Future Stage 9 technical acceptance must demonstrate:

```text
DIRECTOR/ADMIN
→ login
→ kiosk
→ active Group
→ Child Arrival
→ canonical Attendance shows server-local arrival
→ repeated Arrival is idempotent
→ Child Departure
→ repeated Departure is idempotent
→ standard Attendance shows same record

TEACHER
→ only assigned Group available
→ same Arrival/Departure behavior

PARENT
→ kiosk write denied

cross-tenant / unassigned / inactive Group / inactive Child
→ hidden or denied according to existing contract

network failure
→ no false local success / no offline queued PII
```

This is technical acceptance only and does not certify physical security or legal compliance.