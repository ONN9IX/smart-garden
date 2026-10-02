# ПРОМАКС — latent OFF modules product specification

Status: **DESIGN / DEFAULT OFF**

Issue: #159

Baseline: `7537cf156efd0894f579521d6f15ca818c4f11ab`

## 1. Purpose

This document freezes the product behavior of the capabilities that already exist in code/data but are intentionally hidden from the active MVP:

- Polls;
- Incidents;
- Diary;
- Photos;
- Photo consents;
- Document notices.

The goal is **ready-to-enable, not enabled**.

No item in this document authorizes runtime exposure, production/pilot use, new migrations, or new personal-data collection.

## 2. Product rules shared by all latent modules

1. Default state remains OFF.
2. OFF means:
   - no navigation entry;
   - direct frontend routes are unavailable/redirected;
   - API entry returns safe `404 NOT_FOUND`;
   - code/models/data are preserved.
3. Tenant isolation, RBAC, assignment scope and guardian scope remain mandatory after activation.
4. Activation is reversible: disabling the feature hides access again without deleting underlying data.
5. A feature flag is an exposure control, not legal/privacy approval.
6. Synthetic data only for dev/test/preview.
7. OFF/STOP boundaries outside this document remain unchanged.

## 3. Product hierarchy

Latent modules attach to the existing operational hierarchy:

```text
Organization
  └─ Group
      ├─ Teacher assignments
      ├─ Children
      │   └─ Linked guardians
      ├─ Polls
      ├─ Incidents
      ├─ Diary
      └─ Photos
          └─ Photo consent state

Organization / authorized audience
  └─ Document notices
```

No latent module creates a parallel identity, tenant, auth or group model.

---

## 4. Polls

### Purpose

Structured feedback and simple group/organizational questions.

Polls are not a replacement for chat, announcements, voting with legal consequences, elections, consent collection or contracts.

### Roles

- **DIRECTOR / ADMIN**
  - view tenant polls;
  - create a poll for an authorized scope;
  - close a poll;
  - view aggregate results.
- **TEACHER**
  - view polls for assigned groups;
  - create/close polls only within assigned-group scope.
- **PARENT**
  - view polls only when eligibility follows from a linked child/group;
  - cast one active vote per eligible poll.

### UX

Poll card:
- question;
- options;
- audience/group;
- state: Active / Closed;
- deadline if the existing model supports it;
- aggregate result after voting/closure according to product rules.

Default result presentation is privacy-minimized. Do not expose another parent's identity or individual vote in the UI.

### Automation

- poll published → eligible audience sees it;
- optional notification to eligible participants;
- vote → aggregate result refresh;
- poll closed → voting becomes unavailable.

### Explicit non-goals

- anonymous legal voting;
- parent consent capture;
- employee HR voting;
- legally binding approvals;
- public polls across tenants.

---

## 5. Incidents

### Purpose

Operational record of a concrete event that requires staff attention or follow-up.

Examples may include a non-medical operational event or safety-related occurrence that the kindergarten needs to track internally.

### Roles

- **DIRECTOR / ADMIN**
  - tenant-wide operational list;
  - create/update where authorized;
  - monitor state.
- **TEACHER**
  - create/update only for assigned-group context.
- **PARENT**
  - **no incident feed by default**.

Any future PARENT exposure requires a separate product + privacy decision.

### UX

Incident record should prioritize:
- child/group context where necessary;
- date/time;
- concise factual description;
- operational status;
- responsible follow-up.

Do not turn the module into a medical chart, psychology journal or free-form sensitive dossier.

### Automation

- incident created → relevant operational responsible roles may receive an IMPORTANT notification;
- unresolved incident → may appear in DIRECTOR/ADMIN exception-first Today dashboard;
- status changed → dashboard/notification state updates;
- sensitive state changes → audit.

### Explicit non-goals

- diagnosis;
- treatment plan;
- medical history;
- psychology/development profile;
- automatic risk scoring.

---

## 6. Diary

### Purpose

Short daily operational note connected to a child/group day.

It may support simple context for the parent without creating a developmental or psychological profile.

### Roles

- **TEACHER**
  - create/update only for children in currently assigned groups.
- **DIRECTOR / ADMIN**
  - read for legitimate operational need.
- **PARENT**
  - read only for linked child.

### UX

Diary entry is concise:
- date;
- child;
- short note;
- author/context.

The UI should discourage excessive free-form sensitive detail.

### Automation

- entry created/updated → linked Parent view refreshes;
- optional low-priority notification to linked parent;
- audit only where required by frozen audit policy.

### Explicit non-goals

- behavior scoring;
- psychological conclusions;
- developmental ratings;
- diagnosis;
- hidden teacher-only profiling;
- replacement for medical records.

---

## 7. Photos + Photo consents

### Activation unit

`photos` is one product activation unit covering:
- photo viewing/upload;
- photo-consent visibility/management.

**Photos must never be enabled without the consent control path.**

### Roles

- **DIRECTOR / ADMIN**
  - review/manage consent records according to RBAC;
  - operational oversight.
- **TEACHER**
  - see consent status for assigned group;
  - upload only in assigned-group scope and only when the current consent state allows the intended publication.
- **PARENT**
  - view only photos eligible through linked-child/group scope.

### UX

Before upload/publish:
- group context is explicit;
- affected child context is explicit where applicable;
- consent restrictions are visible;
- blocked child/photo scope cannot be bypassed by UI.

### Automation

- consent recorded → eligibility state refreshes;
- consent withdrawn → future access/publication rules update immediately according to the privacy contract;
- photo upload → eligible Parent views refresh;
- relevant actions → audit.

### Explicit non-goals

- public galleries;
- social-media publishing;
- external sharing links;
- face recognition;
- biometric identification;
- training ML models on child photos.

### Hard activation dependency

Real-photo use requires the applicable protected-storage, retention, access-administration and legal/privacy prerequisites to be resolved first.

---

## 8. Document notices

### Purpose

Internal informational notice + acknowledgement workflow.

Examples:
- staff instruction;
- internal organizational notice;
- required-to-read information.

### Roles

- **DIRECTOR / ADMIN**
  - create notices for an authorized recipient/audience;
  - see delivery/acknowledgement state.
- **TEACHER**
  - see notices addressed to them;
  - acknowledge receipt/read status.
- **PARENT**
  - not exposed by default in the current latent contract.

### Semantics

Acknowledgement means:
**“the addressed user acknowledged the notice in ПРОМАКС.”**

It does **not** mean:
- qualified electronic signature;
- contract signature;
- legal consent;
- payment confirmation.

Contracts, Billing, Payments, Debt and Receipts remain STOPPED.

### Automation

- notice published → recipient notification;
- acknowledged → status updates for authorized management;
- overdue/unacknowledged notices may appear as an operational exception;
- create/ack actions are auditable.

---

## 9. Navigation when eventually enabled

### DIRECTOR / ADMIN

Latent modules should be grouped by purpose, not added as six flat top-level items.

Suggested placement:
- **Работа сада**
  - Инциденты
  - Дневник
- **Коммуникации**
  - Опросы
  - Уведомления/документальные извещения
- **Фото**
  - Фотографии
  - Согласия

### TEACHER

Suggested:
- Мои группы / child context → Diary;
- group work → Polls / Incidents;
- Photos;
- Notices in Notifications/More.

### PARENT

Only when enabled:
- Polls;
- Diary inside child context;
- Photos.

No Incidents or Document notices by default.

## 10. Acceptance for this design

The design is ready when:
- every module has one clear job;
- roles and audience are explicit;
- automation does not bypass human authorization;
- privacy-sensitive expansion is explicitly excluded;
- future activation does not require redefining product behavior.
