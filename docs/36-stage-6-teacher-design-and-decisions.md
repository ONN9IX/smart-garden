# Stage 6 — TEACHER design and frozen decisions

**Status:** design-frozen by Issue #121; application implementation has not started.

**Pre-design baseline:** `471bdad125f3682c5924ad1e52dd642e75942e23`.

**Next gate:** `S6-FOUNDATION`, created explicitly by Master Chat after the design PR merges.

## 1. Scope

Stage 6 is **TEACHER Cabinet & Parallel Delivery Foundation**. It designs:

- the `TEACHER` identity and server-side access model;
- explicit many-to-many Employee ↔ Group teacher assignments;
- teacher-only APIs and UI for assigned groups;
- assigned-group roster and guardian communication context;
- assigned-group attendance and schedule read;
- child diary, group/direct communication and group announcements;
- polls, incidents, teacher tasks, notifications and document notices;
- photo-consent state and photo metadata/content-delivery boundary;
- the minimum DIRECTOR/ADMIN management surfaces needed to operate TEACHER access;
- one serialized Foundation gate followed by one autonomous full-cabinet TEACHER delivery and explicitly disjoint ONN9IX Track A work.

This document freezes architecture only. It creates no role, route, table, migration, UI, storage integration or production capability.

## 2. Out of scope

- redesign of any Stage 1–5 contract;
- adding `TEACHER` to existing DIRECTOR/ADMIN management permissions;
- role conversion or multi-role membership such as `ADMIN+TEACHER`;
- a second authentication or tenant system;
- a second attendance or announcement model;
- medical data, diagnosis, medication, treatment or medical documents;
- biometrics, face recognition or automatic child recognition;
- real personal data or real photos in dev/test/preview;
- selection of a production photo/file provider;
- public object URLs or production binary-document storage;
- finance, payments or unrelated future DIRECTOR/ADMIN architecture;
- implementation of `S6-FOUNDATION` or any later Stage 6 Issue.

## 3. Identity model

The existing relation remains authoritative:

```text
Employee.user_id -> User.id
```

A `User` continues to have exactly one platform role. Stage 6 conceptually extends the role set to:

- `DIRECTOR`
- `ADMIN`
- `TEACHER`
- `PARENT`

There is no role-membership array and no second auth system. `organization_id` is resolved only from the authenticated `User`; it is never selected or overridden by a client.

A `TEACHER` User must map to exactly one active Employee in the same tenant. Authentication and current-session resolution must validate server-side:

1. the User exists;
2. `User.status == active`;
3. `Organization.status == active`;
4. `User.role == TEACHER`;
5. an Employee exists with `Employee.user_id == User.id`;
6. `Employee.organization_id == User.organization_id`;
7. `Employee.status == active`.

An existing ADMIN account is not converted to TEACHER. An Employee assignment does not turn an ADMIN User into a TEACHER.

## 4. Employee lifecycle

Archiving the Employee linked to a TEACHER must, in one lifecycle operation:

- deny TEACHER access;
- block the linked User account;
- revoke all active auth sessions for that account.

Restoring an Employee does not silently grant access: account and assignment rules remain explicit. Blocking a TEACHER User denies access independently of Employee or assignment state.

## 5. Employee ↔ Group assignment

Do not add `teacher_id` to `Group`. The frozen relationship is a many-to-many entity:

```text
TeacherGroupAssignment -> teacher_group_assignments
```

Its fields, constraints and indexes are frozen in `docs/38-stage-6-data-model-privacy-and-tests.md`.

Assignment semantics:

- only DIRECTOR grants, archives or restores TEACHER access;
- ADMIN may read assignment information needed for operations but cannot grant or revoke access;
- the target Employee must be active, same-tenant and linked to an active TEACHER User;
- the target Group must be active and same-tenant for teacher access;
- a TEACHER may have zero, one or many active groups;
- a Group may have multiple active TEACHER assignments;
- the unique Employee/Group pair is restored after archive rather than duplicated;
- assignment removal denies access on the next backend request;
- session revocation is not required solely because an assignment is removed.

A TEACHER with no active assignments may authenticate and receives an empty cabinet.

## 6. Server-side authorization primitive

Foundation must provide one reusable guard/service equivalent in semantics to:

```text
require_teacher_group_access(actor, group_id)
```

For every request it verifies:

- `actor.role == TEACHER`;
- the actor has an active same-tenant Employee link;
- an active same-tenant `TeacherGroupAssignment` exists for the Employee and Group;
- the Group is active and belongs to the same tenant.

Frontend visibility is never authorization. Foreign-tenant and unassigned resources use the frozen non-disclosure behavior, including `404` where existence must be hidden. Actor, sender and tenant identity are server-owned.

## 7. Teacher operational modules

The TEACHER cabinet is limited to the authenticated teacher context:

- **Today:** assigned groups plus today's schedule, attendance summary, active own tasks, own notifications and unread eligible communications; implemented only after those modules exist.
- **Groups and roster:** active assigned groups and minimal active child data.
- **Guardian context:** only active ChildGuardian relations for children in assigned groups, with minimized contact data.
- **Attendance:** reuse the existing `Attendance` model and its historical group snapshot semantics.
- **Schedule:** read-only for TEACHER; managed by DIRECTOR/ADMIN.
- **Communication:** current assigned group threads and eligible direct TEACHER↔PARENT threads; participant scope is derived server-side.
- **Diary:** read/write for currently assigned active children; PARENT reads only linked children.
- **Announcements:** reuse the existing `Announcement` model; TEACHER reads and creates only for actively assigned Groups, creates only `target_type=group`, and may update/archive only own announcements while the Group remains actively assigned. PARENT reads active all-garden and eligible active Group announcements.
- **Polls:** TEACHER creates/closes polls for assigned groups; eligible PARENT users cast one non-anonymous single-option vote.
- **Incidents:** TEACHER operates incidents for assigned groups; no medical fields and no raw PARENT incident record in Stage 6.
- **Tasks:** DIRECTOR/ADMIN create and assign; TEACHER changes only the status of an own assigned task.
- **Notifications:** each user sees only own notifications; rows do not duplicate free-text PII.
- **Document notices:** DIRECTOR/ADMIN issue immutable metadata-only notices; the recipient may acknowledge them. No binary document storage is introduced.
- **Photos:** assigned-group and consent-gated metadata/content access through authenticated Backend delivery only.

DIRECTOR/ADMIN operational APIs for canonical Group messages, incidents, document notices and photo-consent state are additive Stage 6 management surfaces. They do not grant blanket access to direct TEACHER↔PARENT message content. Photo-consent writes record an externally established state; they do not implement or prove the legal consent flow.

## 8. Photo boundary

Photos are a separately gated capability:

- active consent is required for every manually identified child in an asset;
- no public URL is stored or returned;
- bytes are delivered only through authenticated Backend authorization;
- no face recognition, biometrics or automatic child identification;
- dev/test/preview use synthetic photos and may use a local/ephemeral adapter;
- production upload fails closed until approved storage provider, data location, access, backup, retention and privacy configuration exists;
- MIME/type and size allowlists are enforced;
- EXIF/metadata is stripped before persistence where technically applicable;
- bytes, object secrets and sensitive storage keys are never logged.

Consent withdrawal immediately blocks new uploads for that child and restricts ordinary TEACHER/PARENT reads of affected assets. Physical deletion and retention remain a separate legal/business decision. DIRECTOR receives only the administrative metadata required to resolve a restricted asset.

The consent registry is technical state, not a conclusion that the form or source of consent is legally sufficient.

## 9. Document boundary

Stage 6 teacher document support contains only notice/acknowledgement metadata. It does not upload, store or expose binary documents. Production binary document storage requires a separate infrastructure- and privacy-approved design.

## 10. Privacy boundary

- Tenant isolation and least privilege apply to every Backend path.
- Dev/test/preview contain synthetic data only.
- No speculative PII fields are introduced.
- Free-text message, diary and incident content is excluded from technical logs and `AuditEvent.details`.
- Audit details contain identifiers, state transitions and changed-field names only.
- No medical module, biometrics or face recognition is introduced.
- Real pilot remains gated by the unresolved Stage 5 legal/privacy/infrastructure checklist and Stage 6 consent/photo/document decisions.
- Technical design or technical acceptance is not proof of full compliance with Federal Law No. 152-FZ.

## 11. Immutable decisions

1. Stages 1–5 remain FROZEN.
2. Authorization is always Backend server-side.
3. Tenant comes only from authenticated User.
4. TEACHER is not added to old DIRECTOR/ADMIN management role lists.
5. One User has one role; TEACHER requires an active same-tenant Employee.
6. Employee ↔ Group assignments are many-to-many via `teacher_group_assignments`.
7. Only DIRECTOR changes teacher accounts and assignments; ADMIN assignment access is read-only.
8. Assignment removal takes effect on the next request.
9. Existing `Attendance` and `Announcement` are reused.
10. Foundation creates the complete teacher-domain schema in one serialized migration before parallel implementation.
11. Shared auth/models/migrations/AppShell/CI/current-state files are reserved after Foundation.
12. Production photo upload remains disabled until the external privacy/infrastructure decisions are approved.
13. Teacher documents remain metadata/acknowledgement only.
14. Stage 6 implementation is not started by this design freeze.
15. After Foundation, F1zname receives one major `S6-TEACHER-CABINET` Issue, branch and PR for the complete cabinet; internal modules are not separate Master Chat gates.
16. Ordinary defects stay in that branch. Early return to Master Chat occurs only for the frozen STOP conditions in Issue #121.
