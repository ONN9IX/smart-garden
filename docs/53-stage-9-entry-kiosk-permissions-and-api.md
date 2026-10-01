# Stage 9 — Entrance Kiosk Permissions and API

**Status:** design proposal for Issue #142; frozen only after the design PR merges.
**Owner:** ONN9IX.
**Implementation:** NOT AUTHORIZED until Stage 6 integrated acceptance is complete.
**API conventions:** `/api/v1`, JSON `snake_case`, UUID identifiers, server-owned tenant/actor/time.

## 1. Authorization invariants

1. Kiosk routes require an authenticated staff User.
2. Tenant is derived only from authenticated User.
3. Client-supplied organization, actor, date or attendance time is never authoritative.
4. DIRECTOR/ADMIN scope is active same-tenant Groups.
5. TEACHER scope is active same-tenant Groups with an active current TeacherGroupAssignment and active Employee.
6. PARENT has no kiosk write access.
7. Every roster and write request revalidates current scope.
8. Frontend visibility is not authorization.

## 2. Role matrix

| Capability | DIRECTOR | ADMIN | TEACHER | PARENT |
|---|---|---|---|---|
| Open kiosk | Yes | Yes | Yes | No |
| List kiosk Groups | all active same-tenant | all active same-tenant | assigned active only | No |
| View kiosk roster | authorized Group | authorized Group | assigned active Group | No |
| Mark Arrival | Yes | Yes | assigned active Group | No |
| Mark Departure | Yes | Yes | assigned active Group | No |
| Historical correction | existing Attendance UI | existing Attendance UI | existing Stage 6 Attendance scope | No kiosk write |
| Change Child/Group data | existing management rules | existing management rules | No | No |
| Physical door unlock | No Stage 9 core | No | No | No |

## 3. Proposed route family

Use a narrow additive namespace:

- `GET /api/v1/entry-kiosk/groups`
- `GET /api/v1/entry-kiosk/groups/{group_id}/roster`
- `POST /api/v1/entry-kiosk/children/{child_id}/arrival`
- `POST /api/v1/entry-kiosk/children/{child_id}/departure`

No separate kiosk Attendance CRUD family is created.

The write routes are commands that delegate to canonical Attendance semantics.

## 4. Group list

### GET /entry-kiosk/groups

Returns:

- `id`
- `name`

DIRECTOR/ADMIN:

- active Groups in authenticated Organization.

TEACHER:

- active Groups with active TeacherGroupAssignment;
- Employee must be active;
- assignment must be active.

No archived Group is returned.

No counts or unrelated operational data are required.

## 5. Kiosk roster

### GET /entry-kiosk/groups/{group_id}/roster

Backend first authorizes the Group for the actor.

Return active Children in that Group with current organization-local Attendance state.

Suggested response:

```json
{
  "date": "2026-10-01",
  "group": {
    "id": "uuid",
    "name": "Ромашка"
  },
  "items": [
    {
      "child": {
        "id": "uuid",
        "first_name": "Иван",
        "last_name": "Тестовый",
        "middle_name": null
      },
      "attendance": {
        "record_id": null,
        "status": "unknown",
        "arrival_time": null,
        "departure_time": null
      }
    }
  ]
}
```

Do not return:

- birth_date by default;
- Guardian information;
- contacts;
- financial data;
- diary/messages;
- incidents;
- photos.

## 6. Search API decision

Stage 9 core does not require a server child-search endpoint.

The authorized roster is already intentionally small enough for the tablet flow.

Search/filter should operate in transient frontend memory over the returned authorized roster.

Benefits:

- no search-query logs containing names;
- no tenant-wide child enumeration route;
- simpler privacy boundary.

If scale later proves this insufficient, server-side search requires a separate privacy review.

## 7. Arrival command

### POST /entry-kiosk/children/{child_id}/arrival

Request body:

- none.

The Backend derives:

- actor;
- tenant;
- current authorized Group;
- organization-local date;
- organization-local current wall time.

Response should contain:

- `action: "arrival"`;
- `changed: boolean`;
- canonical minimized Attendance result.

### Authorization

DIRECTOR/ADMIN:

- Child must be active;
- Child Group active;
- same tenant.

TEACHER:

- all above;
- active Employee;
- active assignment to current Child Group.

PARENT/wrong role:

- denied.

## 8. Departure command

### POST /entry-kiosk/children/{child_id}/departure

Request body:

- none.

Server derives date/time.

Response:

- `action: "departure"`;
- `changed: boolean`;
- canonical minimized Attendance result.

Same authorization rules as Arrival.

## 9. Server-side time

The kiosk API must not accept:

- `date`;
- `arrival_time`;
- `departure_time`;
- client timezone.

Backend computes the current instant and converts it with the authenticated Organization's validated IANA timezone.

Store the current local wall time using existing Attendance semantics.

## 10. Arrival state machine

For garden-local today:

| Current canonical state | Arrival result |
|---|---|
| no record / unknown | present + set server arrival |
| absent | present + set server arrival |
| present, arrival null, departure null | set server arrival |
| present, arrival set, departure null | unchanged, `changed=false` |
| present, departure set | 409 `ATTENDANCE_ALREADY_DEPARTED` |

A retry must never replace the original confirmed Arrival time.

## 11. Departure state machine

| Current canonical state | Departure result |
|---|---|
| no record / unknown | 409 `ARRIVAL_REQUIRED` |
| absent | 409 `ARRIVAL_REQUIRED` |
| present, arrival null | 409 `ARRIVAL_REQUIRED` |
| present, arrival set, departure null | set server departure |
| present, departure set | unchanged, `changed=false` |

A retry must never replace the first confirmed Departure time.

## 12. Concurrency

Implementation must be safe under duplicate/concurrent taps.

For the same Child/today:

- lock/select the canonical Attendance state in a transaction;
- preserve existing unique Child/date constraint;
- ensure two concurrent Arrival commands cannot produce different arrival times;
- ensure two concurrent Departure commands cannot overwrite the first departure;
- return one changed result and subsequent unchanged results.

Exact SQL strategy is implementation detail; invariant is frozen.

## 13. Canonical Attendance delegation

The Stage 9 service may call reusable Attendance functions or factor a shared internal primitive.

It must not copy divergent validation rules.

Frozen existing rules remain:

- one Child/date Attendance;
- tenant scope;
- active Child for new marks;
- active Group for new marks;
- stable historical Group snapshot;
- present-only arrival/departure times;
- departure cannot precede arrival;
- Audit on real create/update;
- garden-local future-date rule.

Kiosk adds stricter current-day-only and server-time behavior.

## 14. Historical correction

No kiosk route accepts a record ID for arbitrary PATCH.

Corrections stay in the existing authorized Attendance API/UI.

If Stage 6 TEACHER Attendance supports assigned-group corrections, that contract remains unchanged.

## 15. Error semantics

Use current error envelope.

At minimum:

- unauthenticated → auth error;
- PARENT/wrong role → 403;
- foreign/hidden Group/Child → active non-disclosure behavior;
- unassigned TEACHER → 404/hidden-resource behavior consistent with Stage 6;
- inactive Child/Group → safe conflict/not-found according to current Attendance contract;
- Departure without Arrival → 409 `ARRIVAL_REQUIRED`;
- Arrival after recorded Departure → 409 `ATTENDANCE_ALREADY_DEPARTED`;
- invalid Organization timezone → fail closed;
- backend/network unavailable → no frontend success.

No error reveals another tenant's resource existence.

## 16. Response minimization

Kiosk Attendance response should omit fields not needed by the entrance UI.

Do not expose:

- `created_by`;
- `updated_by`;
- historical audit details;
- Guardian fields.

Suggested attendance payload:

- record_id;
- date;
- status;
- arrival_time;
- departure_time.

The actor remains available to Audit server-side without being shown on the public-facing tablet screen.

## 17. Audit

Real state changes reuse canonical actions:

- `attendance.create`;
- `attendance.update`.

Audit details remain the existing minimized before/after attendance state.

Do not add Child name or search input.

Pure state-idempotent retry:

- no new Attendance mutation;
- no duplicate business Audit event required.

If a future security audit needs kiosk access/session events, that is a separate operational telemetry decision and must remain PII-minimized.

## 18. Frontend route

Suggested application route:

`/entry-kiosk`

It remains protected by the existing auth/session architecture.

Do not introduce a public anonymous kiosk page.

Role routing:

- DIRECTOR/ADMIN/TEACHER may enter;
- PARENT denied/redirected according to existing AuthGate conventions.

## 19. Frontend state

Allowed transient state:

- authorized Group list;
- selected Group ID;
- current roster;
- local search string;
- current request/loading state.

Do not persist roster/attendance to:

- localStorage;
- sessionStorage;
- IndexedDB;
- service-worker offline cache.

## 20. Inactivity logout contract

The implementation must define one kiosk inactivity timer.

On timeout:

1. clear child roster/search in memory;
2. call existing server logout;
3. return to Login.

Do not implement a local-only fake lock while keeping an indefinitely usable authenticated session.

If logout request fails due network loss, clear UI state immediately and prevent further kiosk actions; next server interaction must require a valid authenticated state.

## 21. Network retry

Arrival/Departure commands are naturally state-idempotent.

The UI may offer Retry after network/5xx uncertainty.

It must not display a success time invented by the browser.

After retry, server response is authoritative.

## 22. No offline write queue

Do not queue kiosk writes in:

- IndexedDB;
- localStorage;
- service worker;
- filesystem.

If network fails, operator follows the fallback operational procedure.

A future offline mode would require:

- encrypted device persistence;
- conflict resolution;
- device revocation;
- timestamp trust;
- sync idempotency;
- retention/destruction;
- privacy review.

That is outside Stage 9 core.

## 23. Required backend negative tests

### Tenant

- foreign Group hidden;
- foreign Child hidden;
- forged child UUID does not cross tenant.

### Role / assignment

- PARENT denied all kiosk routes;
- TEACHER sees assigned Group only;
- archived assignment removes access immediately;
- archived Employee removes access;
- archived Group removes access;
- DIRECTOR/ADMIN same-tenant behavior preserved.

### Time/state

- browser/client cannot submit date/time;
- server-local date used;
- first Arrival sets time;
- repeated Arrival preserves first time;
- Departure without Arrival rejected;
- first Departure sets time;
- repeated Departure preserves first time;
- Arrival after Departure rejected;
- no second Attendance record.

### Privacy

- roster has no Guardian contacts;
- roster has no medical/financial/diary fields;
- no sensitive search logging;
- Audit contains no Child name.

## 24. Required browser flow

```text
staff login
→ Entry kiosk
→ authorized Group
→ filter Child
→ Arrival
→ server-confirmed state/time
→ repeated Arrival remains unchanged
→ Departure
→ server-confirmed state/time
→ repeated Departure remains unchanged
→ logout / inactivity lock
```

TEACHER browser coverage additionally verifies another Group is absent/denied.

PARENT route coverage verifies kiosk is inaccessible.

## 25. Compatibility

Stage 9 must preserve:

- existing management Attendance API;
- Stage 6 TEACHER Attendance;
- Stage 8 future PARENT attendance read;
- Organization.timezone;
- Audit semantics;
- tenant isolation;
- RBAC;
- synthetic-only development.

No Stage 9 API may weaken any existing Attendance permission.