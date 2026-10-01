# Stage 11 — Development Support Delivery Plan

**Status:** design proposal for Issue #146; frozen only after the design PR merges.
**Owner:** ONN9IX.
**Design baseline:** `7a37789a5fb24334cb245bd251b5f4b0eb18657a`.

## 1. Design now, implementation later

Stage 11 design may freeze while Stage 6 is still completing because it is docs-only.

Runtime implementation does not start before Stage 6 integrated acceptance/freeze.

Stage 11 is a differentiator, but it must not delay the core operational/commercial path unnecessarily.

Default product priority after Stage 6:

```text
Stage 10 protected storage foundation
→ Stage 7 financial foundation / contracts-billing
→ Stage 8 parent consolidation
→ Stage 11 development-support implementation
```

Master Chat may move Stage 11 earlier after Stage 6 if a psychology-department pilot/demo becomes the immediate product priority, but only when the migration/shared-file lane is free.

## 2. Design gate

Issue #146 owns exactly:

- docs/60-stage-11-development-support-product-spec.md
- docs/61-stage-11-development-support-permissions-and-api.md
- docs/62-stage-11-development-support-data-privacy.md
- docs/63-stage-11-development-support-delivery-plan.md

No code, migration, tests, CI, dependencies or shared coordination changes.

## 3. Runtime prerequisite

Before implementation:

1. Stage 6 is accepted/frozen.
2. Current User/role/Employee/assignment/ChildGuardian contracts are revalidated.
3. Current migration head is recorded.
4. Exact observation enums/fields receive final privacy/product review.
5. No other active Issue owns the migration/model-registry lane.
6. Current parent/teacher namespaces are known after Stage 8/Stage 6 work.
7. No new SPECIALIST role is required for the first implementation.

## 4. One major implementation Issue

Preferred implementation:

`S11-DEVELOPMENT-SUPPORT — methodology, teacher activities and parent recommendations`

One major Issue, one fresh branch, one migration, one PR.

**PARALLEL-SAFE:** NO while it owns migration/model registry/shared router registration.

This minimizes Work runs and avoids a separate foundation/cabinet split unless preflight proves a shared integration gate is necessary.

## 5. Expected schema

One serialized migration may create:

- MethodologyItem;
- MethodologyVersion;
- DevelopmentActivity;
- DevelopmentObservation;
- ParentRecommendation;
- ParentRecommendationFeedback;

plus required indexes/constraints.

Do not add:

- diagnosis table;
- psychological profile table;
- score table;
- specialist role;
- research export table.

## 6. Shared integration preflight

Before the major Issue, inspect current main for:

- model registry;
- router aggregation;
- teacher/parent route extension points;
- management navigation extension point;
- Audit action allowlist/integration;
- Notification extension mechanism.

If one minimal shared change is required outside the product write-set, create a small serialized integration Issue first.

Do not mix unrelated auth/RBAC redesign into Stage 11.

## 7. Preferred namespaces

Exact paths come from fresh main.

Preferred isolated backend shape:

- backend/app/api/development/**
- backend/app/schemas/development/**
- backend/app/services/development/**
- Stage 11 tests

Teacher/parent adapters may use current role-specific namespaces only when exact write-set ownership is clear.

Preferred frontend shape:

- frontend/src/app/development/**
- frontend/src/features/development/**
- frontend/src/features/teacher/development/**
- frontend/src/features/parent/development/**
- frontend/src/lib/api/development/**
- frontend/src/types/development/**
- Stage 11 browser tests

Do not create another auth/API client.

## 8. Internal implementation order

1. schema + migration;
2. methodology draft/version lifecycle;
3. DIRECTOR publish/ADMIN draft permissions;
4. TEACHER published library;
5. activity planning;
6. structured observation;
7. assigned Child timeline;
8. parent recommendation publish;
9. parent recommendation read;
10. bounded parent feedback;
11. operational aggregate analytics;
12. Audit/Notification;
13. management UI;
14. TEACHER UI;
15. PARENT UI;
16. responsive/mobile;
17. privacy/RBAC negatives;
18. browser E2E;
19. frozen-stage regression;
20. full CI.

## 9. Methodology UI

Management UI should support:

- methodology list;
- draft create/edit;
- version history;
- review/provenance metadata;
- publish/archive;
- domain/age filters.

Published content must be visibly immutable.

Creating edits to a published methodology starts a new version.

## 10. TEACHER UI

Assigned TEACHER workflow:

```text
Development
→ published methodology
→ select assigned Group/Child
→ plan activity
→ complete activity
→ choose structured outcome
→ optional bounded support tags
→ optionally publish home recommendation
```

No free-text Child assessment box.

No score slider.

## 11. PARENT UI

PARENT workflow:

```text
My child
→ Development / Recommendations
→ approved home activity
→ purpose/materials/steps
→ completed / skipped / needs clarification
```

No internal observation outcome/support tags.

No comparison with other Children.

## 12. DIRECTOR and ADMIN split

DIRECTOR:

- publish/archive methodology;
- view provenance;
- view aggregates;
- intentional individual history access;
- Audit.

ADMIN:

- create/edit drafts;
- operational counts/metadata;
- no individual observation detail by default;
- no publish.

Tests must enforce this distinction server-side.

## 13. No specialist role implementation

Do not modify User.role enum/check constraints/auth navigation for a psychology specialist in the first Stage 11 implementation.

External department collaboration is content/provenance only.

If an authenticated specialist is later required:

STOP → new explicit role/RBAC/privacy design.

## 14. No AI implementation

Do not add:

- LLM summaries of Child timeline;
- automatic recommendation generation from Child observations;
- classification/scoring;
- external AI APIs.

If future AI is used for non-PII methodology drafting, create a separate gate.

## 15. Observation schema hardening

Use strict request models with extra fields forbidden.

Tests must reject attempts to send:

- note/comment;
- diagnosis;
- score;
- risk;
- medical fields;
- arbitrary support/domain tags.

This makes the non-clinical boundary executable, not just documentation.

## 16. Versioning tests

Verify:

- published MethodologyVersion cannot be PATCHed;
- new edits create another version;
- historical DevelopmentActivity remains tied to original version;
- recommendation keeps the version originally published;
- archived version remains readable where historical authorization permits.

## 17. Assignment and relation revocation

TEACHER:

- assignment active → allowed;
- assignment archived → next protected request denied;
- Employee archived → denied;
- Child moved to unassigned Group → denied.

PARENT:

- ChildGuardian active → recommendation allowed;
- relation archived → next request denied.

No cached authorization.

## 18. Required backend tests

Methodology:
- tenant isolation;
- ADMIN draft allowed/publish denied;
- DIRECTOR publish allowed;
- published immutable;
- invalid tags/age fields rejected.

Teacher:
- assigned activity allowed;
- unassigned/foreign Child denied;
- unpublished version denied;
- one observation per activity/Child;
- bounded outcome/support only;
- free-text/score/diagnosis fields rejected.

Parent:
- linked recommendation read;
- unrelated Child denied;
- internal observation absent;
- own bounded feedback;
- other Guardian feedback identity hidden.

Analytics:
- only aggregate operational counts;
- no child ranking endpoint/schema.

Audit/privacy:
- no Child profile text;
- synthetic-only.

## 19. Required browser tests

DIRECTOR:

```text
login
→ Development methodology
→ create draft
→ publish
→ aggregate usage
```

ADMIN:

```text
login
→ edit draft
→ publish attempt denied/absent
→ no individual observation detail
```

TEACHER:

```text
login
→ published methodology
→ plan assigned activity
→ record structured outcome/support
→ publish parent recommendation
```

PARENT:

```text
login
→ recommendation for linked Child
→ read home activity
→ submit bounded feedback
→ verify internal observation absent
```

## 20. Privacy UI checks

No UI should contain:

- diagnosis field;
- score field;
- risk level;
- ranking;
- free-text Child psychological note;
- emotion/face analysis;
- “норма/отклонение” verdict.

Automated browser/static assertions may protect these boundaries where practical.

## 21. Analytics boundary

Implement only operational aggregation.

Do not create an analytics query that sorts named Children by observation outcome.

If future research needs cohort-level analysis, it gets its own design and legal/privacy review.

## 22. Notifications

Use existing Notification if compatible.

Recommended event:

- parent recommendation available.

Do not duplicate observation outcome into notification payload.

If shared Notification schema requires change, serialize it in preflight rather than creating a parallel migration.

## 23. Audit

Reuse current append-only Audit.

DIRECTOR-only ordinary Audit read remains unchanged.

Add only allowlisted Stage 11 actions and structured IDs/status changes.

Do not log methodology full text unnecessarily in Audit; version ID is enough.

## 24. Regression

Keep green:

- auth/session;
- tenant isolation;
- Groups/Children/Guardians;
- TEACHER assignment;
- PARENT ChildGuardian;
- direct-message privacy;
- photo consent;
- Attendance;
- Stage 5 security/backup;
- Stage 7/8/10 contracts if already implemented.

Stage 11 must not weaken another role/domain to pass.

## 25. STOP conditions

Return to Master Chat if implementation requires:

- new User role;
- clinical/medical field;
- diagnosis;
- risk score;
- child ranking;
- unrestricted observation free text;
- AI over Child PII;
- biometrics/emotion recognition;
- external specialist access to Child data;
- research export;
- unapproved new migration head;
- shared auth/RBAC redesign;
- privacy/legal decision not yet resolved;
- real Child data in dev/test.

## 26. Ordinary defect rule

Fix in the same branch:

- draft/version UI bug;
- assigned-child filter;
- enum validation;
- responsive layout;
- API serialization;
- local authorization bug consistent with frozen contract;
- missing test;
- CI defect caused by current diff.

Independent role/medical/research/privacy architecture issues return to Master Chat.

## 27. Validation before PR

Backend:

- ruff;
- Stage 11 targeted pytest;
- migration round trip;
- role/tenant negative regression.

Frontend:

- lint;
- build;
- Stage 11 Playwright specs.

Also:

- git diff --check;
- exact write-set;
- synthetic fixture review;
- dependency/security checks;
- full required CI.

## 28. S11-ACCEPTANCE

Technical acceptance verifies:

- complete methodology lifecycle;
- immutable publication/versioning;
- TEACHER assignment scope;
- structured observation only;
- PARENT recommendation/feedback;
- DIRECTOR/ADMIN permission split;
- no score/rank/diagnosis;
- no free-text Child profile;
- tenant/relation revocation;
- privacy-safe Audit/logging;
- mobile usability;
- frozen regression.

## 29. Psychology methodology validation is separate

Software acceptance does not certify that a particular exercise/methodology is scientifically or professionally valid.

Content quality/review remains a methodology governance process with the psychology department/qualified experts.

Smart Garden records provenance/versioning; it does not claim clinical validation.

## 30. Future expansion gates

Separate future design required for:

- authenticated SPECIALIST role;
- structured specialist consultation;
- any clinical data;
- formal psychometric tests;
- research exports;
- AI methodology assistant;
- AI over Child records;
- media/emotion analysis.

## 31. Desired result

Stage 11 should deliver a credible differentiation:

```text
reviewed methodology
+ controlled teacher practice
+ structured non-clinical observation
+ useful parent home recommendations
- diagnosis
- score
- ranking
- AI profiling
```

This is suitable for collaboration with psychology experts while keeping Smart Garden inside a conservative educational-support boundary.