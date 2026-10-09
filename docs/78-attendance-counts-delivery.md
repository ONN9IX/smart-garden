# Attendance Counts — Issue #195

## Read model

The existing `Attendance.status` values and write API are unchanged. `present` continues to mean that a child attended during the local day. Read-only summaries now also expose `on_site`, `departed`, and `needs_arrival` alongside `absent` and `unknown`.

For every currently active child in a group:

| Read state | Classification |
| --- | --- |
| `on_site` | `present` with an arrival time and no departure time |
| `departed` | `present` with a departure time (takes precedence if legacy data has no arrival time) |
| `absent` | `absent` |
| `unknown` | no attendance row or status `unknown` |
| `needs_arrival` | `present` with no arrival and no departure time |

Exactly one state applies per active child. Therefore `active_children` equals the sum of these five state counts. Aggregates use the organization-local date and match an attendance snapshot to the child's current group; attendance history from a previous group is not carried into the new group.

## Role views and actions

- Director and administrator Today/group summaries distinguish children still on site from children who have left. The existing `present` total remains available as “Посещали сегодня”. Existing authorization for attendance edits, Audit, and Settings is unchanged.
- Teacher Today uses the same read model. In the attendance list, arrival and departure can be recorded from the child row. The UI shows the server's refreshed row only after a successful write and reload. Changing a row with recorded times to absent asks for confirmation because this clears those times under the existing API contract.
- Parent Today displays the selected child's server-provided arrival/departure times and maps a completed departure to “Ушёл”. Child switching hides mismatched data immediately and stale responses are ignored; 403/404 responses clear the private attendance view.

## Verification coverage

- PostgreSQL dashboard regression covers missing and explicit-unknown rows, absent, present without arrival, arrival, departure, local-date boundary, archived children, tenant isolation, current-group snapshots after transfer, five-state balance, organization totals, and no Audit side effect.
- Existing PostgreSQL attendance and cabinet suites cover idempotent attendance mutations, active teacher assignment checks, guardian access checks, and attendance time validation. Additional teacher/management assertions check that role summaries use the same classification.
- Playwright regressions cover director count labels, inline teacher arrival/departure and rejected writes, parent child switching with a delayed response, and widths 320/360/390/430 px.
- No database migration is required; no status or historical record is rewritten.

## Limits

Attendance rows only represent a day's current saved status and times. These calculated buckets do not add a new persisted `left` status or a historical analytics model. Local PostgreSQL and Chromium availability is environment-dependent; the required GitHub CI result remains the integration gate.
