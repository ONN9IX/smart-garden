# ПРОМАКС — latent OFF modules RBAC, API and automation contract

Status: **DESIGN / DEFAULT OFF**

Issue: #159

## 1. Security invariant

Feature activation never weakens the existing access model:

```text
authenticated User
  → tenant derived from User
  → role gate
  → assignment / guardian eligibility
  → object tenant scope
  → action permission
```

A feature flag controls exposure only. It must not replace RBAC or tenant filtering.

When OFF, the API boundary continues to return safe `404 NOT_FOUND` before route authorization for disabled paths.

## 2. Current feature-gate mapping

| Activation unit | Backend key | Frontend key |
|---|---|---|
| Polls | `polls` | `polls` |
| Incidents | `incidents` | `incidents` |
| Diary | `diary` | `diary` |
| Photos + consents | `photos` | `photos` |
| Document notices | `document_notices` | `documentNotices` |

These keys remain OFF until a separate activation Issue.

## 3. RBAC matrix

Legend:
- R = read
- C = create
- U = update/action
- — = no product exposure

| Module | DIRECTOR | ADMIN | TEACHER | PARENT |
|---|---|---|---|---|
| Polls | R/C/U tenant scope | R/C/U tenant scope | R/C/U assigned groups | R + vote eligible polls |
| Incidents | R/C/U tenant scope | R/C/U tenant scope | R/C/U assigned groups | — |
| Diary | R tenant scope | R legitimate operational scope | R/C/U assigned children | R linked child only |
| Photos | oversight | oversight | R/C assigned group + consent | R eligible linked-child/group photos |
| Photo consents | R/C/U | R/C/U per management RBAC | R assigned-group state | no management action |
| Document notices | R/C | R/C | R + acknowledge addressed notices | — |

Any permission expansion beyond this matrix requires a new Master Chat decision.

## 4. Existing API surfaces to preserve

### TEACHER

Diary:
- `GET /api/v1/teacher/diary`
- `POST /api/v1/teacher/diary`
- `PATCH /api/v1/teacher/diary/{entry_id}`

Polls:
- `GET /api/v1/teacher/polls`
- `POST /api/v1/teacher/polls`
- `POST /api/v1/teacher/polls/{poll_id}/close`

Incidents:
- `GET /api/v1/teacher/incidents`
- `POST /api/v1/teacher/incidents`
- `PATCH /api/v1/teacher/incidents/{incident_id}`

Document notices:
- `GET /api/v1/teacher/document-notices`
- `POST /api/v1/teacher/document-notices/{notice_id}/ack`

Photos:
- `GET /api/v1/teacher/photo-consents`
- `POST /api/v1/teacher/photos`
- `GET /api/v1/teacher/photos`
- `GET /api/v1/teacher/photos/{photo_id}/content`

### PARENT

Diary:
- `GET /api/v1/parent/children/{child_id}/diary`

Polls:
- `GET /api/v1/parent/polls`
- `POST /api/v1/parent/polls/{poll_id}/vote`

Photos:
- `GET /api/v1/parent/photos`
- `GET /api/v1/parent/photos/{photo_id}/content`

No Parent Incident or Document-notice surface is part of this contract.

### DIRECTOR / ADMIN management

Diary:
- `GET /api/v1/teacher-management/diary`
- `GET /api/v1/teacher-management/diary/{entry_id}`

Polls:
- `GET /api/v1/teacher-management/polls`
- `GET /api/v1/teacher-management/polls/{poll_id}`
- `POST /api/v1/teacher-management/polls`
- `POST /api/v1/teacher-management/polls/{poll_id}/close`

Incidents:
- `GET /api/v1/teacher-management/incidents`
- `GET /api/v1/teacher-management/incidents/{incident_id}`
- `POST /api/v1/teacher-management/incidents`
- `PATCH /api/v1/teacher-management/incidents/{incident_id}`

Document notices:
- `GET /api/v1/teacher-management/document-notices`
- `POST /api/v1/teacher-management/document-notices`

Photo consents:
- `GET /api/v1/teacher-management/photo-consents`
- `POST /api/v1/teacher-management/photo-consents`
- `POST /api/v1/teacher-management/photo-consents/{consent_id}/withdraw`

## 5. Object-scope rules

### TEACHER

For every group/child-bound request:
- active TEACHER user;
- active employee relationship;
- active teacher-group assignment;
- requested object belongs to the same tenant;
- requested child belongs to an eligible assigned group where required.

A foreign or unassigned UUID must follow the existing non-disclosing API contract.

### PARENT

For every child/group-bound request:
- active PARENT user;
- active Guardian relationship;
- active ChildGuardian link;
- requested child/group/photo/poll is reachable through that link;
- same tenant.

No query may widen scope merely because an object UUID is known.

### DIRECTOR / ADMIN

- same tenant always;
- action-level role rules still apply;
- DIRECTOR-only security/account boundaries are unchanged by these modules.

## 6. Target domain events

These are product event names for automation design. They do not imply a new event bus must be implemented.

Polls:
- `poll.created`
- `poll.voted`
- `poll.closed`

Incidents:
- `incident.created`
- `incident.updated`
- `incident.resolved`

Diary:
- `diary.created`
- `diary.updated`

Photos:
- `photo_consent.recorded`
- `photo_consent.withdrawn`
- `photo.uploaded`

Document notices:
- `document_notice.created`
- `document_notice.acknowledged`

## 7. Automation side effects

| Event | Dashboard | Notification | Audit |
|---|---|---|---|
| poll.created | optional audience count | eligible audience | creator + scope |
| poll.voted | aggregate refresh | normally none | privacy-minimized |
| poll.closed | state refresh | optional participants | yes |
| incident.created | management exception | responsible roles | yes |
| incident.updated/resolved | exception state refresh | relevant responsible roles | yes |
| diary.created/updated | Parent child context refresh | optional Parent INFO | policy-dependent |
| photo_consent.recorded | eligibility refresh | normally none | yes |
| photo_consent.withdrawn | eligibility/access refresh | responsible staff if needed | yes |
| photo.uploaded | eligible gallery refresh | optional Parent INFO | yes |
| document_notice.created | management status | addressed users | yes |
| document_notice.acknowledged | management completion state | normally none | yes |

## 8. Notification policy

Use existing product severity concepts:

- INFO — new diary/photo/poll availability when notification is useful;
- ACTION — vote or acknowledge action requested;
- IMPORTANT — operational incident or unresolved required acknowledgement;
- SECURITY — not used merely because a latent module exists.

Do not notify DIRECTOR about every routine event. Prefer responsible-role routing and escalation.

## 9. Human-readable layer

Backend enums/event names may remain technical.

UI must map them centrally to Russian product labels before activation.

Examples:
- `poll.closed` → «Опрос завершён»
- `incident.created` → «Создана запись об инциденте»
- `photo_consent.withdrawn` → «Согласие на фото отозвано»
- `document_notice.acknowledged` → «Извещение подтверждено»

Raw enum/event identifiers must not leak into normal user-facing UI.

## 10. Default-OFF invariant

Even if an internal service/model works:
- hidden frontend route must not be treated as access control;
- feature-disabled API must stay inaccessible;
- no background automation should create user-visible latent-module notifications while that module is OFF;
- no Today dashboard card should reveal disabled-module state.

Activation tests must cover this invariant.
