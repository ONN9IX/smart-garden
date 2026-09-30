# Stage 6 — DIRECTOR / ADMIN Data, Privacy and Security Contract

**Status:** design proposal for Issue #123; frozen only after PR merge.  
**Owner:** ONN9IX.  
**Purpose:** data minimization, tenant isolation, RBAC, Audit/logging/browser-storage boundaries and mandatory negative tests.

This is a technical privacy/security contract, not a legal opinion or authorization for real personal data.

## 1. Core privacy questions

For every Management feature answer:

1. What data is required?
2. Why is it required?
3. Can less data achieve the same function?
4. Who may read it?
5. Who may change it?
6. How is tenant scope derived?
7. What enters Audit?
8. What enters technical logs?
9. What enters browser storage?
10. What happens after archive/block/revoke?
11. Does the function require a separate retention/legal decision?

Do not add fields "for future use".

## 2. Tenant root

Every business object is scoped to Organization.

Effective tenant always comes from:

`authenticated User.organization_id`

Never from:

- request body;
- query tenant selector;
- hidden form;
- frontend state;
- localStorage.

Frontend may display the Organization but cannot authorize it.

## 3. Tenant isolation

Object access must include tenant predicate on Backend.

Foreign object behavior:

- hidden/non-disclosing denial, normally 404.

This applies at minimum to:

- Group
- Child
- Guardian
- Employee
- TeacherGroupAssignment
- Attendance
- GroupScheduleItem
- Announcement
- CommunicationThread/Message
- ChildDiaryEntry
- Poll/Option/Vote
- Incident
- TeacherTask
- Notification
- DocumentNotice
- PhotoConsent/Asset
- AuditEvent

FK existence alone is not sufficient; cross-entity operations must also validate same-tenant consistency.

## 4. Existing models and Stage 6 Foundation schema

Track A reuses existing Stage 1–5 models and the Stage 6 Foundation schema.

Track A must not create duplicate tables such as:

- director_tasks;
- admin_notifications;
- management_incidents;
- management_schedule;
- teacher_profiles;
- duplicate management Groups/Attendance/Announcements.

Expected Track A result after Foundation:

**NO new migration.**

If implementation requires a new table/column/enum/constraint/index or second Alembic head:

STOP -> Master Chat.

## 5. Organization data

Existing fields remain sufficient:

- id;
- name;
- status;
- timezone;
- timestamps.

Management Settings writes only:

- name;
- timezone.

Do not add address, coordinates, legal/bank details or ownership fields in this Core.

Timezone is IANA and does not require GPS/address.

## 6. Child data minimization

Use existing necessary fields:

- id;
- organization_id;
- group_id;
- first_name;
- last_name;
- middle_name optional;
- birth_date;
- status;
- timestamps.

Do not add:

- passport;
- SNILS;
- insurance;
- medical diagnosis;
- medication;
- allergies;
- doctor details;
- document scans;
- free-form notes;
- biometric data.

Birth date may appear in Child detail but should not be copied into Dashboard, Notifications, Audit or unrelated lists.

## 7. Guardian data minimization

Keep existing:

- names;
- optional phone;
- optional email;
- status;
- Child relations.

Do not add passport, address, workplace, income, bank details, family notes.

Phone/email should appear only in approved contact/card screens and should not be duplicated into Audit, Notifications or logs.

## 8. Employee data minimization

Keep existing:

- id;
- organization_id;
- optional user_id;
- names;
- position;
- status;
- timestamps.

Do not add passport, phone, email, home address, birth date, salary, bank details, medical data or personal notes to Stage 6 Management Core.

"Teacher" remains a projection over Employee + TEACHER User + assignment, not a new personal-data entity.

## 9. User/account data

Management UI may receive safe account summary:

- user_id;
- username;
- role;
- status;
- must_change_password.

Never expose:

- password_hash;
- session token/hash;
- cookie;
- secrets;
- Argon2 internals.

### Temporary password

Allowed only as one-time create/reset response.

Frontend must not persist it in:

- localStorage;
- sessionStorage;
- IndexedDB;
- URL;
- logs;
- telemetry;
- Audit.

Reset must preserve frozen session revocation/must-change-password behavior.

## 10. Employee/account lifecycle

Existing linked-account protections remain frozen.

ADMIN must not bypass account-security restrictions by archiving an Employee linked to a privileged User.

Archive/block/revoke behavior must remain atomic where frozen Stage 1–5/Stage 6 lifecycle requires it.

Restore Employee must not silently unblock account or grant assignment.

## 11. Attendance privacy

Attendance fields remain:

- child_id;
- historical group_id snapshot;
- date;
- status;
- arrival_time;
- departure_time;
- created_by/updated_by;
- timestamps.

Do not add:

- absence reason free text;
- diagnosis;
- illness;
- temperature;
- doctor note;
- Parent explanation.

Child transfer never rewrites historical Attendance Group snapshot.

## 12. Schedule data

Schedule contains operational Group/time/title metadata only.

No Child PII, medical data or free-form Teacher reports.

## 13. Communication privacy

Group and direct communication are separate.

DIRECTOR/ADMIN may operate canonical Group thread according to docs/41.

Direct TEACHER↔PARENT content remains participant-scoped; management has no blanket access.

Message body:

- stored as business content;
- not written to technical logs;
- not copied into Audit.details;
- not duplicated into Notification payload.

Audit may record safe metadata such as message/thread identifiers and actor.

## 14. Diary privacy

Diary note:

- visible only to authorized business UI;
- excluded from technical logs;
- excluded from Audit.details;
- not duplicated into Notification;
- not treated as a medical record.

Management access is read-only in Stage 6.

## 15. Poll privacy

Poll votes are technically non-anonymous to enforce one PARENT User vote per Poll.

Normal management UI exposes aggregate results only.

Full voter identity must not be exposed by default without a separate explicit business/privacy requirement.

Option must belong to Poll; cross-Poll mismatch is rejected.

## 16. Incident privacy

Incident may contain:

- Group;
- optional Child;
- occurred_at;
- category;
- description;
- status;
- reporter/resolver identifiers;
- timestamps.

No structured:

- diagnosis;
- medication;
- treatment;
- disease;
- medical history;
- doctor;
- medical document.

Incident description is sensitive free text:

- business UI only for authorized roles;
- no technical logs;
- no Audit.details copy;
- no Notification body copy.

## 17. Teacher Task privacy

Task fields remain operational.

Task description must not be used as storage for medical data, passport data, contact details, documents or private communication.

Audit should prefer changed_fields/state transitions over copying title/description.

## 18. Notifications

Notification rows contain:

- recipient;
- kind;
- entity type/id;
- read state;
- created time.

Do not duplicate source business text/PII into Notifications.

Own-recipient scoping is mandatory even for DIRECTOR/ADMIN.

## 19. Document Notices

DocumentNotice is metadata/acknowledgement only.

No:

- file;
- blob;
- PDF;
- passport scan;
- contract content;
- evidence attachment.

Full binary document management requires a separate architecture/privacy/legal design.

## 20. Photo-consent technical state

PhotoConsent records technical state such as:

- Child;
- granted/withdrawn;
- scope=group_photo_report;
- effective period;
- recorder;
- timestamps.

A granted database row does not prove that the product itself obtained legally sufficient consent.

Legal form/source/evidence remains a real-pilot decision.

## 21. Photo boundary

Track A manages consent state and minimal administrative metadata only.

No blanket Management access to photo bytes.

No:

- public object URL;
- face recognition;
- face embedding;
- biometric templates;
- automatic Child identification.

Dev/test/preview use synthetic photos only.

Production upload remains fail-closed until approved:

- provider;
- data location;
- access model;
- backup;
- retention;
- privacy/legal configuration.

## 22. Browser storage

Do not persist sensitive data in localStorage/sessionStorage/IndexedDB, including:

- session token;
- password;
- temporary password;
- full Child/Guardian persistent cache;
- message body;
- diary note;
- incident description;
- photo bytes;
- document content.

HttpOnly cookie remains authoritative.

In-memory UI state is allowed for current screen use.

## 23. URLs and query values

Do not place in URLs:

- names;
- phone/email;
- message body;
- diary note;
- incident description;
- temporary password;
- sensitive document titles;
- storage secrets.

Allowed where appropriate:

- UUID;
- date;
- enums;
- pagination;
- non-sensitive status.

Search endpoints may technically accept q under existing frozen APIs, but observability must avoid persisting PII-rich query values unnecessarily.

## 24. Technical logging

Allowed minimum:

- request_id;
- method;
- route/path template;
- status;
- duration;
- safe user_id/org_id when operationally necessary;
- safe error code.

Never log:

- password/hash/temp password;
- cookie/token/Authorization;
- full PII request bodies;
- message body;
- diary note;
- incident description;
- photo bytes;
- document contents;
- unnecessary phone/email.

Errors must return safe structured information and never traceback/SQL/connection strings/secrets.

## 25. Audit

Audit remains append-only and DIRECTOR-only read.

Audit and technical logs are different systems.

Audit.details is an explicit allowlist, not arbitrary JSON.

Preferred details:

- changed_fields;
- status_before;
- status_after;
- account_role;
- safe UUID identifiers;
- target_type or safe enum.

Forbidden in Audit.details:

- passwords;
- temporary passwords;
- password hashes;
- tokens/cookies;
- message body;
- diary note;
- incident description;
- announcement body;
- task description;
- unnecessary phone/email;
- photo bytes;
- storage secrets;
- document content.

Stage 6 Audit writer changes must extend explicit action/detail allowlists deliberately.

## 26. Data retention boundary

Stage 6 does not invent retention periods.

Do not choose arbitrary 30/90-day or multi-year rules without business/legal approval.

Archive != legal destruction.

Block != deletion.

Before real pilot determine retention/destruction for at least:

- Child/Guardian/Employee data;
- messages;
- diary;
- incidents;
- poll votes;
- notifications;
- document notices;
- photos;
- Audit;
- backups.

## 27. External services

Do not connect without explicit review:

- external analytics;
- session replay;
- error tracking with payloads;
- external photo/file cloud;
- messaging SaaS;
- external AI processing PII.

No AI processing of Child/Guardian/Employee PII is part of this Track.

## 28. Dev/test/preview

Synthetic data only.

Do not use:

- production DB copies;
- real Child/Parent/Employee records;
- real phone/email;
- real photos;
- real documents;
- real conversations.

Screenshots/demos must also be synthetic.

## 29. Mandatory negative tests — tenant

At minimum verify hidden denial for cross-tenant access to:

- Group;
- Child;
- Guardian;
- Employee;
- Attendance;
- Assignment;
- Schedule;
- Poll;
- Incident;
- Task;
- Diary;
- Notification where applicable;
- AuditEvent.

Client-supplied organization_id never changes effective tenant.

## 30. Mandatory negative tests — role

- ADMIN -> Audit = 403
- ADMIN -> TEACHER account lifecycle = 403
- ADMIN -> assignment writes = 403
- ADMIN -> settings write = 403
- TEACHER -> management APIs = 403
- PARENT -> management APIs = 403

Account regression:

- PARENT account: DIRECTOR PASS, ADMIN PASS
- ADMIN account: DIRECTOR PASS, ADMIN 403
- TEACHER account: DIRECTOR PASS, ADMIN 403

## 31. Assignment tests

Reject:

- foreign Employee;
- foreign Group;
- archived Employee;
- Employee without active TEACHER User;
- archived Group;
- ADMIN write.

Assignment removal must take effect on the next Teacher request.

## 32. Child transfer tests

Reject foreign/archived target Group.

After transfer:

- old Teacher loses access;
- historical Attendance Group snapshot remains unchanged;
- Guardian relation remains unchanged.

## 33. Direct-message privacy tests

DIRECTOR/ADMIN arbitrary direct TEACHER↔PARENT thread access is denied.

Canonical Group thread management remains allowed.

## 34. Free-text leakage tests

Verify that test sentinel strings placed in:

- communication body;
- diary note;
- incident description;
- temporary password

do not appear in technical logs or Audit.details.

## 35. Notification tests

User A cannot read/mark User B Notification.

Client cannot override recipient.

Notification row does not contain source business body duplicate.

## 36. Document Notice tests

Reject file/file_url/blob/passport_scan/document_content fields.

Recipient for this Core must be active same-tenant TEACHER User.

## 37. Poll tests

- foreign Group hidden;
- Option/Poll mismatch rejected;
- duplicate PARENT vote rejected according to Stage 6 contract;
- management default result remains aggregate.

## 38. Photo-consent tests

- TEACHER/PARENT write = 403;
- foreign Child hidden;
- write audited;
- no evidence blob accepted;
- production photo upload fails closed without approved config.

## 39. Settings tests

- DIRECTOR GET/PATCH allowed;
- ADMIN/TEACHER/PARENT PATCH = 403;
- organization_id supplied as authority rejected;
- invalid IANA timezone rejected;
- change audited without copying unnecessary Organization data.

## 40. Regression contract

Keep green:

- Stage 1 auth/session;
- Stage 2 Groups/Children/Guardians/PARENT;
- Stage 3 Employees/ADMIN account/Attendance/timezone;
- Stage 4 Audit/Announcements/Dashboard;
- Stage 5 production security/CI/backup-recovery;
- Stage 6 Foundation contracts once merged;
- TEACHER Track B permissions.

## 41. 152-FZ / real-pilot boundary

Technical Stage 6 acceptance does not prove full legal compliance and does not authorize real PII.

Before real pilot separately resolve:

- operator/controller/processor roles;
- legal basis;
- minor/guardian processing;
- hosting/data location;
- subprocessors/data flows;
- retention/destruction;
- backup protection/location;
- access administration;
- incident process;
- legal source/evidence of photo consent;
- binary document architecture;
- Roskomnadzor notification where applicable.

Any implementation need to resolve these legal/business decisions triggers STOP -> Master Chat.
