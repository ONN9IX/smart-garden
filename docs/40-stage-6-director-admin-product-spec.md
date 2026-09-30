# Stage 6 — DIRECTOR / ADMIN Cabinet Product Specification

**Status:** design proposal for Issue #123; becomes frozen only after the design PR merges.
**Owner:** ONN9IX.
**Track:** Stage 6 Track A — DIRECTOR / ADMIN.
**Implementation:** NOT STARTED.
**Compatibility:** Stages 1–5 remain frozen; TEACHER Track B remains independently owned.

## 1. Goal

Turn the existing management UI into a complete daily operating cabinet for a kindergarten DIRECTOR and ADMIN without redesigning frozen Stage 1–5 behavior.

The cabinet must support:

- operational Dashboard / Today;
- Groups;
- Children;
- Guardians / parents;
- Employees;
- Teachers management projection;
- TEACHER account lifecycle and Group assignments;
- Attendance;
- Schedule;
- Announcements;
- Group communication management;
- Diary management read;
- Polls;
- Incidents;
- Teacher tasks;
- Management notifications;
- Document notices;
- Photo-consent state;
- Audit;
- Organization settings;
- responsive desktop/tablet/mobile use.

Authorization is always enforced on Backend. Frontend visibility is UX only.

## 2. Roles

### DIRECTOR

DIRECTOR is the highest management role inside one tenant, not a platform Super Admin.

DIRECTOR may:

- manage all approved operational entities of the own Organization;
- manage ADMIN accounts under frozen Stage 1–5 semantics;
- manage TEACHER accounts;
- grant/archive/restore TEACHER Group assignments;
- read Audit;
- manage Organization name and timezone;
- use all approved Stage 6 management surfaces.

DIRECTOR may not:

- choose or switch tenant;
- read another Organization;
- access platform/infrastructure secrets;
- receive blanket access to direct TEACHER↔PARENT message content.

### ADMIN

ADMIN is the daily operational role.

ADMIN may:

- manage Groups, Children, Guardians and Employees under frozen rules;
- manage Attendance;
- manage Schedule;
- manage Announcements;
- manage Tasks;
- manage Incidents;
- manage Polls;
- use canonical Group communication management;
- read operational Diary entries;
- use own Notifications;
- issue/list Stage 6 metadata-only Document Notices within the frozen recipient boundary;
- manage technical photo-consent state under same-tenant rules.

ADMIN may not:

- read Audit;
- change Organization settings;
- create/reset/block/unblock ADMIN accounts;
- create/reset/block/unblock TEACHER accounts;
- grant/revoke TEACHER Group assignments;
- elevate own privileges;
- read blanket direct TEACHER↔PARENT conversations.

## 3. Navigation

### DIRECTOR

- Главная
- Группы
- Дети
- Родители
- Сотрудники
- Воспитатели
- Посещаемость
- Расписание
- Объявления
- Задачи
- Происшествия
- Опросы
- Уведомления
- Аудит
- Настройки

### ADMIN

- Главная
- Группы
- Дети
- Родители
- Сотрудники
- Воспитатели
- Посещаемость
- Расписание
- Объявления
- Задачи
- Происшествия
- Опросы
- Уведомления

ADMIN does not receive Audit, Settings, ADMIN-account controls, TEACHER-account controls or assignment-write controls.

## 4. UX principles

1. Daily actions should be reachable in a few clear transitions.
2. Dashboard shows actionable state, not decorative metrics.
3. Lists use explicit filters instead of duplicate pages.
4. Archived data is hidden by default.
5. Destructive actions require confirmation.
6. Raw JSON, traceback and internal exception messages are never shown to users.
7. Garden-local dates use Organization timezone.
8. Desktop, tablet and mobile remain operationally usable.
9. Every main screen has loading, empty, success and error states.
10. Frontend never becomes the authorization boundary.

## 5. Dashboard / Today

Dashboard answers:

> What is happening in the kindergarten now and what needs attention?

Show privacy-minimized cards:

- active Children;
- present today;
- absent today;
- unknown / without attendance mark;
- active Groups;
- active Employees;
- open Tasks;
- unread own Notifications;
- open Incidents when Stage 6 model is available.

### Attention block

Structured operational alerts may include:

- missing attendance marks;
- overdue Tasks;
- open Incidents;
- Group without active TEACHER assignment;
- blocked TEACHER account where management action is required.

Do not place message body, diary note, incident description, phone/email or other unnecessary PII into Dashboard attention payloads.

### Groups today

Per Group:

- name;
- active children count;
- present / absent / unknown;
- assigned active Teachers;
- open Group action link.

## 6. Groups

### List

Show:

- name;
- status;
- active child count;
- attendance today;
- assigned Teachers;
- whether at least one active teacher assignment exists.

Filters:

- active;
- archived;
- all.

Search by Group name.

### Group card

Tabs/sections:

- Overview
- Children
- Teachers
- Attendance
- Schedule
- Parents
- Announcements
- Tasks
- Polls
- Incidents

### Assignment actions

DIRECTOR:

- assign Teacher;
- archive assignment;
- restore assignment.

ADMIN:

- read assignment information only.

The UI must select eligible Employees/Teachers; users do not type raw User IDs or tenant IDs.

## 7. Children

### List

Show:

- full name;
- Group;
- status;
- attendance today;
- linked Guardian count.

Filters:

- Group;
- status;
- attendance.

Search by name.

### Child card

Sections:

- Basic;
- Guardians;
- Attendance;
- Diary;
- Photo consent state when Stage 6 capability is available.

Basic data remains frozen/minimal:

- name;
- birth date;
- current Group;
- status.

Do not add medical, passport, insurance, free-form notes or biometric fields.

### Group transfer

Use the existing Child update semantics. After transfer:

- old Teacher access is lost on the next Backend request;
- new Teacher access follows the new Group assignment;
- historical Attendance keeps its original Group snapshot;
- Guardian relations remain unchanged.

## 8. Guardians / parents

### List

Show:

- name;
- optional phone;
- optional email;
- linked Children;
- PARENT account status.

### Card

Sections:

- Basic;
- Linked Children;
- Account.

Never show:

- password;
- password hash;
- session token;
- raw auth internals.

ChildGuardian relation management continues under frozen Stage 1–5 rules.

## 9. Employees

### List

Show:

- name;
- position;
- Employee status;
- account existence;
- account role;
- for TEACHER, number of assigned Groups.

Filters:

- active / archived / all;
- account exists / absent;
- account role.

### Card

Sections:

- Basic;
- Account;
- Assigned Groups for TEACHER.

Existing Employee lifecycle and linked-account protections remain frozen.

## 10. ADMIN account management

Existing Stage 1–5 behavior remains:

DIRECTOR may:

- create ADMIN account;
- reset password;
- block;
- unblock.

ADMIN may not manage ADMIN accounts.

Temporary password:

- one-time display;
- never stored in browser persistent storage;
- never logged;
- never copied to Audit details.

## 11. Teachers management projection

The "Воспитатели" section is a projection over:

`Employee + User(role=TEACHER) + TeacherGroupAssignment`

It is not a new Teacher DB entity.

List shows:

- Employee name;
- position;
- Employee status;
- TEACHER account status;
- assigned Groups.

DIRECTOR actions:

- create TEACHER account;
- reset password;
- block/unblock;
- assign Group;
- archive/restore assignment.

ADMIN: read only for account/assignment controls.

## 12. Attendance

Reuse existing Attendance.

Management screen:

- selected date;
- Group filter;
- Child filter;
- status filter.

Summary:

- total active children;
- present;
- absent;
- unknown.

Rows:

- Child;
- Group snapshot;
- status;
- arrival;
- departure.

DIRECTOR/ADMIN keep existing management write permissions.

No absence reason, diagnosis or medical free text is added.

## 13. Schedule

Management screen filters:

- Group;
- weekday.

Schedule item:

- Group;
- weekday;
- start time;
- end time;
- title;
- status.

DIRECTOR/ADMIN:

- create;
- update;
- archive.

TEACHER read behavior belongs to Track B.

Schedule never infers Attendance.

## 14. Announcements

Reuse existing Announcement model.

DIRECTOR/ADMIN may:

- list active/archive;
- create all-garden announcement;
- create Group announcement;
- update;
- archive.

List shows:

- title;
- audience;
- status;
- created date;
- author identifier/presentation.

Archive is read-only lifecycle; no hard delete.

TEACHER announcement rules remain Track B and must not be weakened.

## 15. Group communication management

DIRECTOR/ADMIN may read/post only to the canonical same-tenant Group thread.

No management screen gives blanket access to direct TEACHER↔PARENT thread content.

Messages are immutable in Stage 6.

Sender identity is Backend-owned.

## 16. Diary management read

DIRECTOR/ADMIN may read Diary entries for same-tenant Children according to docs/41.

Management is read-only in Stage 6.

The note is visible only in the authorized business UI and is not copied into Audit or technical logs.

## 17. Polls

DIRECTOR/ADMIN may:

- list Polls;
- create Group Poll;
- close Poll;
- read aggregate result.

Default result UI shows:

- option;
- vote_count;
- total_votes.

Do not expose full voter identities by default even though Stage 6 voting is technically non-anonymous.

## 18. Incidents

Management list shows:

- occurred date/time;
- Group;
- optional Child;
- category;
- status;
- reporter metadata where allowed.

Filters:

- Group;
- status;
- category;
- date range.

DIRECTOR/ADMIN may create/update under the frozen API.

Incident is not a medical module. No diagnosis, medication, treatment or medical-document fields.

## 19. Teacher tasks

List shows:

- title;
- assignee;
- optional Group;
- due date;
- status.

Filters:

- assignee;
- Group;
- status;
- due period.

DIRECTOR/ADMIN may:

- create;
- assign;
- update;
- cancel.

TEACHER may change only status of own assigned Task through Track B.

Overdue is computed from due_at and garden-local current time; it is not a separate stored status.

## 20. Management notifications

Each management user sees only own Notifications.

List:

- kind;
- date;
- read/unread;
- safe link to permitted entity.

Notification is a pointer/state record, not a copy of sensitive business content.

## 21. Document notices

Stage 6 management notices are metadata/acknowledgement only.

For this Core, management issue/list targets active same-tenant TEACHER Users.

No:

- binary file;
- PDF upload;
- passport scan;
- contract body;
- public file URL.

Full document management is a later design gate.

## 22. Photo-consent management

Track A manages:

- technical consent state;
- effective period;
- limited administrative metadata required to resolve restricted assets.

Track A does not receive blanket photo-content access.

Consent state does not prove legal sufficiency of the consent flow.

Production photo upload remains fail-closed until storage/data-location/access/backup/retention/privacy decisions are approved.

## 23. Audit

DIRECTOR only.

ADMIN receives 403.

List filters:

- date;
- actor;
- action;
- entity type.

Show:

- time;
- actor;
- action;
- entity type;
- safe entity identifier;
- privacy-safe details.

Never display/store in Audit details:

- passwords;
- temporary passwords;
- tokens/cookies;
- message body;
- diary note;
- incident description;
- unnecessary contacts;
- photo bytes;
- document content.

## 24. Organization settings

DIRECTOR only.

Fields:

- Organization name;
- Organization timezone.

Timezone must be valid IANA.

No address/GPS is required.

Never expose:

- DATABASE_URL;
- SECRET_KEY;
- CORS secrets;
- backup credentials;
- deployment settings.

## 25. Archive behavior

For archive-capable entities:

- archived hidden by default;
- explicit archived/all filter;
- archive requires confirmation;
- restore appears only where frozen contract permits it;
- archive is not legal destruction/deletion.

## 26. Responsive behavior

Must remain usable on:

- desktop;
- tablet;
- mobile.

Priority mobile/tablet screens:

- Dashboard;
- Groups;
- Attendance;
- Tasks;
- Announcements;
- Incidents.

Large tables must degrade into responsive rows/cards rather than relying on permanent horizontal scrolling.

## 27. Error and empty states

Every major screen covers:

- loading;
- empty;
- success;
- error.

401 -> login/auth flow.
403 -> safe forbidden state.
404 -> safe not-found/non-disclosure state.

Frontend must not reveal that a hidden UUID belongs to another tenant.

## 28. Product out of scope

Not part of Stage 6 Management Core:

- finance;
- billing;
- payments;
- fiscal receipts;
- debt;
- financial accounting;
- full binary document storage;
- contracts/e-signatures;
- medical module;
- AI;
- entrance/access-control tablet;
- biometrics/face recognition;
- external production photo/file provider.

## 29. Product completion

The DIRECTOR Core is functionally complete when DIRECTOR can:

1. authenticate;
2. use Dashboard;
3. manage Group;
4. manage Child;
5. manage Guardian;
6. manage Employee;
7. manage ADMIN account;
8. manage TEACHER account;
9. manage TEACHER assignment;
10. manage Attendance;
11. manage Schedule;
12. manage Announcement;
13. manage Task;
14. manage Incident;
15. manage Poll;
16. use Group communication;
17. read Diary;
18. use Notifications;
19. issue/list TEACHER Document Notices;
20. manage photo-consent state;
21. read Audit;
22. manage name/timezone;
23. logout.

ADMIN must pass the corresponding operational flow while all DIRECTOR-only actions remain Backend-forbidden.

## 30. Design boundary

This document defines product behavior only.

Technical contracts are frozen separately in:

- docs/41-stage-6-director-admin-permissions-and-api.md
- docs/42-stage-6-director-admin-data-privacy.md
- docs/43-stage-6-director-admin-delivery-plan.md

Implementation must not start from this document alone.
