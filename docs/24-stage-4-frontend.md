# Stage 4 — Frontend specification

Design source: docs/22-stage-4-data-model-and-decisions.md
API source: docs/25-api-contract-stage-4.md

## 1. Navigation

DIRECTOR/ADMIN:
- Dashboard /dashboard
- Announcements /announcements

DIRECTOR additionally sees:
- Audit /audit

ADMIN must not see Audit navigation.
PARENT stays in technical parent area and gets no Stage 4 management UI.
Settings remains disabled/future.

## 2. Dashboard

Replace welcome-only dashboard with operational summary while retaining useful organization/user context.

Show:
- garden-local date
- active children
- present
- absent
- unknown/no mark
- active groups
- active employees
- group statistics

No historical graphs/trends.

States: loading, success, empty, safe error + retry.
Responsive desktop/tablet/mobile, no horizontal overflow.

## 3. Announcements

Routes:
- /announcements
- /announcements/new
- /announcements/[id]

List:
- active default
- status active/archived/all
- target all/group
- show title, target label/group, status, created_at
- no free-text search in URL

Create/edit:
- target whole kindergarten or active group
- title
- body
- switching target to all clears group
- group required for group target
- length limits reflected in UI
- save disabled during request
- safe error retains values
- archive requires confirmation
- archived announcement read-only

Privacy notice near body:
“Не указывайте пароли, медицинские сведения и другие избыточные персональные данные.”

No attachments, rich HTML, push/email/SMS controls.

## 4. Audit UI

DIRECTOR only at /audit.

Columns:
- timestamp
- actor username/role
- action
- entity type
- entity id
- compact approved details

Filters:
- entity type
- action
- date from/to
- actor UUID only if it can be selected without adding a broad new user-directory API; otherwise omit this UI filter while keeping backend support

Pagination: limit/offset controls.

Do not resolve entity IDs into child/guardian/employee names.
No edit/delete.
ADMIN direct URL denied/redirected; backend independently returns 403.

## 5. Browser privacy

Do not put announcement title/body, names or audit details in URL.
Only enums, UUIDs, dates, limit/offset may be query parameters.
Do not persist forms/announcements/audit rows in browser storage.
Do not console-log announcement body/audit details.
Dev/test screenshots/data synthetic only.

## 6. API modules/types

Dedicated typed modules for dashboard, announcements, audit.
Reuse common API/session behaviour.

## 7. Real browser E2E

Cover:
1. DIRECTOR Stage 4 navigation.
2. ADMIN Announcements/Dashboard but no Audit.
3. PARENT no Stage 4 management UI/API.
4. Dashboard counters match synthetic state.
5. Create whole-garden announcement.
6. Create group announcement.
7. Edit active announcement.
8. Archive confirmation and read-only archived state.
9. Cross-tenant announcement denied.
10. DIRECTOR Audit shows representative Stage 2/3/4 mutations.
11. ADMIN Audit API 403.
12. Audit renders no passwords, announcement body or business-person names from details.
13. Dashboard uses garden-local date.
14. desktop/tablet/mobile overflow and no runtime errors.

Stage 1–3 regression remains green through CI.
