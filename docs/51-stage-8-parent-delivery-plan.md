# Stage 8 — PARENT Cabinet Delivery Plan

**Status:** design proposal for Issue #139; frozen only after the design PR merges.
**Owner:** ONN9IX.
**Design baseline:** `16b11ea1d5e66e4c9b98d773be87dd4c2587b936`.

## 1. Required order

```text
Stage 6 TEACHER delivery
→ Stage 6 integrated acceptance
→ Stage 6 FROZEN
→ Stage 8 design #139 merged/frozen
→ parent implementation preflight
→ required serialized shared dependency, if any
→ S8-PARENT-CABINET
→ PR CI + review + merge
→ post-merge CI
→ S8-ACCEPTANCE
```

Stage 7 financial implementation is an independent dependency. The PARENT cabinet may be implemented in a non-financial form first only if Master Chat explicitly freezes the integration boundary; Stage 7 financial routes must never be reimplemented or approximated inside Stage 8.

## 2. Design gate

Issue #139 owns exactly:

- `docs/48-stage-8-parent-cabinet-product-spec.md`
- `docs/49-stage-8-parent-permissions-and-api.md`
- `docs/50-stage-8-parent-data-privacy.md`
- `docs/51-stage-8-parent-delivery-plan.md`

No code, migration, tests, CI, dependencies or shared coordination files.

## 3. Stage 6 dependency

No Stage 8 runtime implementation starts until:

1. #131 is complete and merged;
2. post-merge CI is green;
3. Stage 6 integrated acceptance verifies DIRECTOR/ADMIN/TEACHER/PARENT together;
4. Stage 6 is frozen;
5. exact current `main` baseline is recorded.

This protects the PARENT implementation from colliding with active Stage 6 PARENT communication/diary/poll/photo work.

## 4. Stage 7 dependency

Before Stage 8 implementation, Master Chat records one of two states.

### A. Stage 7 implemented

PARENT cabinet may integrate frozen Contracts/Billing routes directly.

### B. Stage 7 not yet implemented

PARENT cabinet ships without finance navigation/content. No placeholder fake balances, local payment model or duplicate API is allowed.

Later Stage 7 integration gets its own exact Issue/write-set.

## 5. Preflight

Inspect only current post-Stage-6 source of truth:

- PARENT routes/files delivered by #131;
- current AppShell/navigation extension points;
- Notification and DocumentNotice recipient capabilities;
- Attendance/Schedule read services;
- current PARENT tests;
- current Stage 7 implementation status;
- current migration head only if a shared dependency is proven necessary.

Preflight must determine whether PARENT Document Notices can be enabled without shared schema changes.

## 6. Shared dependency gate

Expected Stage 8 core should require **no new migration**.

If PARENT Document Notice recipients require a model/schema migration or reserved-file change, serialize a small prerequisite Issue before S8-PARENT-CABINET.

Do not smuggle that change into the large cabinet branch.

## 7. Primary implementation Issue

Create one major Issue:

`S8-PARENT-CABINET — complete parent daily cabinet`

Preferred delivery:

- one Issue;
- one fresh branch;
- one PR;
- one exact write-set;
- ordinary defects fixed in the same branch.

Internal modules are milestones, not separate Master Chat gates.

## 8. Implementation scope

The major cabinet Issue should deliver:

1. coherent PARENT navigation;
2. Home/Today aggregator;
3. eligible child list/selector;
4. child overview;
5. PARENT Attendance read;
6. PARENT Schedule read;
7. integration of Stage 6 Announcements;
8. integration of Group/direct communication;
9. Diary read;
10. Poll vote;
11. Photos;
12. Notifications;
13. Document Notices if preflight says safe;
14. Stage 7 finance integration only if Stage 7 exists;
15. responsive/mobile pass;
16. tenant/RBAC/relation/privacy negative tests;
17. PARENT E2E and cross-role regression.

## 9. Reuse rule

Do not create duplicate models/APIs for:

- ChildGuardian;
- Attendance;
- Schedule;
- Announcement;
- Communication;
- Diary;
- Poll;
- Photo;
- Notification;
- DocumentNotice;
- Stage 7 Contract/Billing resources.

Stage 8 is primarily a coherent PARENT access/presentation layer plus narrowly approved read endpoints.

## 10. Suggested implementation namespaces

Exact paths are frozen in the future Issue after Stage 6 merge.

Prefer existing PARENT namespaces established by #131:

- `backend/app/api/parent/**` or the exact existing equivalent;
- `backend/app/schemas/parent/**`;
- `backend/app/services/parent/**`;
- `frontend/src/app/parent/**`;
- `frontend/src/features/parent/**`;
- `frontend/src/lib/api/parent/**`;
- `frontend/src/types/parent/**`;
- Stage 8-specific tests.

Do not touch TEACHER namespaces unless a shared contract requires serialization.

## 11. Recommended internal order

1. inspect/reuse post-#131 PARENT structure;
2. eligible child selector;
3. Attendance read;
4. Schedule read;
5. Today aggregator;
6. navigation integration;
7. Announcements;
8. Group/direct communication;
9. Diary;
10. Polls;
11. Photos;
12. Notifications;
13. Notices;
14. Stage 7 conditional integration;
15. mobile UX;
16. negative/privacy tests;
17. E2E;
18. regression;
19. required CI.

## 12. Today aggregator rule

Implement Today last enough that all source modules are known.

The aggregator must be composition-only:

- no duplicate source-of-truth tables;
- no message/diary free text;
- no photo bytes;
- no invented finance data;
- every child-specific source individually authorization-safe.

## 13. Attendance delivery

PARENT Attendance must reuse existing Attendance.

Required tests:

- linked child read allowed;
- unlinked child hidden;
- foreign tenant hidden;
- no write;
- no medical/reason field;
- historical data cannot authorize other Group resources.

## 14. Schedule delivery

Reuse existing Schedule.

Required tests:

- current eligible child/group only;
- stale/forged Group cannot expand access;
- PARENT read only;
- group transfer updates eligibility on next request.

## 15. Communication/Diary/Polls/Photos

Treat Stage 6 #131 implementation as authoritative.

Stage 8 may improve navigation/composition but must not change:

- participant rules;
- assignment rules;
- sender ownership;
- diary author/access semantics;
- poll vote uniqueness;
- consent/photo rules.

Any required Stage 6 contract change triggers STOP → Master Chat.

## 16. Notifications and notices

Reuse own-user recipient semantics.

If PARENT notice support is safe without migration, implement in cabinet.

If not, exclude it from the main branch and create a serialized shared dependency Issue.

No binary documents.

## 17. Financial integration

When Stage 7 exists:

- reuse its PARENT routes;
- show finance only for contracting Guardian;
- do not cache finance across child switch;
- preserve Stage 7 errors/non-disclosure.

When Stage 7 does not exist:

- finance entry is absent;
- no fake/local Stage 8 finance API.

## 18. Required backend negative tests

At minimum:

- foreign tenant;
- unlinked Child;
- inactive relation;
- forged Guardian/User/organization fields;
- Attendance write denied;
- Schedule foreign group denied;
- direct-thread non-participant denied;
- group eligibility after relation/group changes;
- unlinked Diary denied;
- cross-group/duplicate Poll vote denied;
- consent-withdrawn Photo denied;
- another User Notification denied;
- another User Notice denied;
- non-contracting Guardian finance denied;
- safe errors/no resource enumeration.

## 19. Privacy tests

Use sentinel tests to verify message/diary content does not enter:

- technical logs;
- Audit.details;
- Today aggregator;
- Notification duplicated body.

Also verify:

- no persistent browser PII storage;
- no public photo/document URL;
- no medical fields;
- synthetic-only fixtures.

## 20. Required PARENT E2E

```text
login
→ Home
→ Child A
→ Attendance
→ Schedule
→ Announcements
→ Group communication
→ Direct Teacher communication
→ Diary
→ Poll vote
→ Photos
→ Notifications
→ Notice acknowledgement when enabled
→ switch Child B
→ verify isolation
→ Stage 7 finance only if entitled/available
→ logout
```

Run responsive coverage for desktop/tablet/phone.

## 21. Cross-role regression

Keep green:

- DIRECTOR management cabinet;
- ADMIN restrictions;
- TEACHER assigned-group behavior;
- direct-thread privacy;
- PARENT Stage 6 communication/diary/poll/photo;
- Stage 1–5 security and backup/recovery;
- Stage 7 financial permissions when implemented.

## 22. STOP conditions

Return to Master Chat if implementation requires:

- changing auth/session architecture;
- changing tenant derivation;
- changing Stage 6 participant/assignment rules;
- weakening consent/photo boundary;
- granting management access to PARENT;
- widening DIRECTOR/ADMIN direct-message access;
- changing Stage 7 contracting-Guardian rule;
- new medical/biometric data;
- new migration not already serialized;
- production external photo/document provider;
- real PII in dev/test/preview;
- unresolved retention/legal/hosting decision required for implementation.

## 23. Ordinary defect rule

Fix in the same cabinet branch:

- responsive issue;
- child-switch bug;
- missing loading/empty/error state;
- API serialization bug;
- authorization bug consistent with frozen contract;
- missing targeted test;
- CI defect caused by current implementation.

Independent architecture/security/privacy/migration findings return to Master Chat.

## 24. Validation

During work run targeted tests.

Before PR:

Backend:
- `ruff check .`;
- all Stage 8 PARENT tests;
- relevant Stage 6/7 regression.

Frontend:
- `npm run lint`;
- `npm run build`;
- PARENT browser specs;
- relevant TEACHER/management regression.

Also:
- `git diff --check`;
- exact write-set check;
- synthetic-data check;
- required full repository CI.

## 25. S8-ACCEPTANCE

Serialized final gate after required Stage 8 implementation merges.

Verify:

- coherent PARENT daily flow;
- multi-child isolation;
- tenant/relation enforcement;
- Attendance/Schedule read;
- preserved Stage 6 participant/photo rules;
- own Notifications/Notices;
- Stage 7 financial isolation if integrated;
- mobile usability;
- no sensitive browser persistence;
- no real PII;
- required CI/security/backup regression.

## 26. Acceptance boundary

Technical Stage 8 acceptance does not prove full 152-FZ compliance or authorize a real pilot.

Real deployment still depends on approved legal, hosting, retention, provider and operational controls.