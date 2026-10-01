# Stage 11 — Development Support Data, Privacy and 152-FZ Boundary

**Status:** design proposal for Issue #146; frozen only after the design PR merges.
**Owner:** ONN9IX.
**Scope:** technical privacy/product boundary only.
**Implementation:** NOT AUTHORIZED until Stage 6 integrated acceptance is complete.

## 1. Privacy posture

Child development observations can be sensitive even when they are not medical records.

Stage 11 therefore applies stricter minimization than ordinary operational data.

The system records only what is necessary to document participation in a specific approved educational activity.

It does not create a general psychological profile of a Child.

## 2. Purpose limitation

Stage 11 data is used only for:

- planning approved development activities;
- recording bounded activity outcomes;
- maintaining an educational activity timeline;
- publishing approved home recommendations;
- collecting bounded parent completion feedback;
- methodology quality/usage operations.

Do not reuse this data for:

- admissions;
- pricing;
- discipline;
- employee evaluation;
- child ranking;
- marketing;
- advertising;
- medical decisions;
- automated risk scoring.

## 3. Data categories

### Methodology content

Non-child-specific educational content:

- title/purpose;
- age band;
- steps/materials;
- domain tags;
- home variant;
- source/review organization.

This is not Child PII by itself.

### Activity metadata

May identify a Group/Child and date.

Treat as personal operational data.

### Structured observation

Contains bounded outcome/support tags for a specific Child/activity.

Treat as private Child development data.

### Parent recommendation

Links a Child to an approved educational/home activity.

Treat as private Child/family data.

### Parent feedback

Links an eligible Guardian/User to bounded completion state.

Treat as private family data.

## 4. No clinical data in core

Stage 11 schemas do not contain:

- diagnosis;
- symptoms;
- disorder;
- treatment;
- medication;
- clinical test result;
- psychiatric/psychological diagnosis code;
- medical certificate;
- therapy note;
- mental-health risk score.

If future requirements need clinical/health data, they require a separate legal/privacy/architecture gate.

## 5. No free-text Child profile

The core DevelopmentObservation has no unrestricted note field.

Reason:

- free text can unintentionally contain health data;
- free text can become a subjective Child profile;
- visibility/retention becomes difficult to control;
- structured enums are enough for the first product.

Do not add a “Комментарий о ребёнке” convenience field during implementation.

## 6. Neutral enums

Outcome/support values must remain neutral descriptions of the activity event.

Allowed outcome meaning:

- participated;
- completed with support;
- completed independently;
- not observed.

Forbidden labels include:

- normal/abnormal;
- delayed;
- problem child;
- high/low intelligence;
- anxiety/depression;
- ADHD/autism;
- risk level.

Do not introduce equivalent labels under different wording.

## 7. No numeric score

Do not persist or display:

- development total score;
- percentage of “normal”;
- percentile;
- readiness score;
- psychological risk score;
- ranking position.

No formula combines activity outcomes into a score.

## 8. No cross-child comparison

The UI must not create:

- leaderboards;
- best/worst Child;
- group percentile;
- heatmap comparing named Children;
- sorted list by outcome quality.

Operational aggregate counts may describe methodology usage, not Child quality.

## 9. No cross-domain profiling

Do not combine Stage 11 with:

- Attendance frequency;
- Incidents;
- Diary;
- Messages;
- Photos;
- payment/contract data;
- parent activity

to infer behavior/personality/development.

Future research/analytics use needs a separate legal/privacy/research design.

## 10. Teacher access

TEACHER sees only currently assigned active Groups/Children.

Every request revalidates:

- User;
- Employee;
- assignment;
- Group;
- Child;
- tenant.

Assignment revocation removes ordinary access on the next request.

Historical access policy must be explicitly frozen at implementation; it must not automatically preserve broad access merely because the teacher authored an old observation.

## 11. Director access

DIRECTOR may access individual activity history only for legitimate organization oversight.

General dashboards should prefer aggregate operational data.

DIRECTOR access does not mean Child records should be displayed on every management surface.

## 12. Admin access

ADMIN does not receive individual DevelopmentObservation outcomes by default.

ADMIN may handle:

- methodology drafts;
- operational activity/recommendation counts;
- scheduling/metadata where approved.

This is intentional data minimization despite ADMIN's broad operational role elsewhere.

## 13. Parent access

PARENT may access only:

- published recommendations;
- approved home activity content;
- own feedback state;

for currently linked active Child.

PARENT does not receive:

- internal teacher observation outcome;
- support tags;
- another Guardian's account details;
- another Child's recommendation;
- Group-level development analytics.

## 14. Parent feedback privacy

Feedback is tied to authenticated Guardian/User.

Do not show one Guardian the identity or detailed feedback of another Guardian.

If a future family-level aggregate status is added, it should say only what the workflow requires, without exposing another account.

## 15. Psychology department / external specialist boundary

External psychology-department collaboration in Stage 11 core is **methodology-only**.

External specialists do not receive production tenant accounts or Child data merely because their department reviewed content.

Store organization-level provenance where possible.

Do not send external reviewers:

- Child observations;
- names;
- parent data;
- screenshots;
- production exports.

A future specialist account/research collaboration requires a separate data-access and RBAC gate.

## 16. Methodology provenance minimization

Prefer:

- review organization;
- source reference;
- reviewed_at;

rather than personal reviewer contacts.

If individual reviewer attribution is later contractually required, store only minimum professional attribution and review its purpose/retention separately.

## 17. Browser storage

Do not persist Child development payloads in:

- localStorage;
- sessionStorage;
- IndexedDB;
- offline caches.

This includes:

- observations;
- recommendations;
- parent feedback;
- child activity timeline.

HttpOnly session remains authoritative.

## 18. Technical logs

Never log:

- full observation payload by default;
- Child names unnecessarily;
- parent recommendation content;
- parent feedback body (there is no free text);
- auth tokens/cookies.

Allowed minimal diagnostics:

- request_id;
- route template;
- status;
- duration;
- safe actor/org ID where needed;
- target UUID after authorization;
- safe error code.

## 19. Audit

Audit records accountability, not a psychological profile.

Allowed details:

- target IDs;
- activity/methodology IDs;
- status transition;
- changed field names;
- bounded enum before/after where justified.

Avoid repeating Child names.

No free-text child content exists in the core.

## 20. Notifications

Notifications should say only:

- “Доступна новая рекомендация”
- “Рекомендация обновлена”
- “Есть домашняя активность”

Do not put internal observation outcome or sensitive interpretation into notifications.

External push/email/SMS channels require provider privacy review.

## 21. Analytics

Allowed analytics are operational and methodology-focused.

Examples:

- number of published activities;
- number of completed activities;
- usage by methodology;
- count of parent recommendations;
- parent completion-status totals.

Do not expose named-Child outcome distributions.

No third-party analytics receives raw Child development events.

## 22. AI boundary

Do not send Child development data to external AI.

Do not use models to infer:

- diagnosis;
- personality;
- behavior risk;
- development delay;
- parent quality;
- teacher quality.

Future AI over methodology content only may be considered separately if no Child/parent PII is included.

## 23. Photos/audio/video

Stage 11 does not collect media for assessment.

Do not use:

- camera observation;
- speech analysis;
- emotion recognition;
- motion tracking;
- facial analysis.

Activity outcome is manually recorded by authorized staff.

## 24. Data retention

Issue #146 does not invent retention periods.

Before real pilot, define retention/destruction for:

- activity records;
- observations;
- recommendations;
- parent feedback;
- methodology history;
- Audit;
- backups.

Published methodology history may have different retention needs from Child-specific records.

## 25. Child relation lifecycle

If Child becomes archived/leaves the Organization:

- ordinary operational access changes according to approved lifecycle;
- records are not silently physically deleted;
- retention/destruction follows the approved policy;
- historical business integrity is preserved without widening access.

## 26. Subject access/export

Future export/subject request must:

- include only entitled Child/Guardian data;
- preserve other Guardian privacy;
- preserve staff/security information where required;
- avoid exposing internal platform secrets.

Stage 11 does not create a bulk research export API.

## 27. Research boundary

A psychology department may later want anonymized/pseudonymized research data.

That is outside Stage 11 core.

It requires a separate explicit research design covering:

- purpose;
- legal basis;
- dataset fields;
- de-identification risk;
- small cohort risk;
- export recipient;
- retention;
- ethics/consent where applicable.

Do not call simple UUID removal “anonymous” by default.

## 28. Dev/test/preview

Synthetic-only:

- Child names;
- methodology;
- activity outcomes;
- recommendations;
- feedback.

Do not use real Child observations or psychology-department research datasets in fixtures.

## 29. Dashboard privacy

General management dashboard may show operational counts.

Do not display:

- named Child outcomes;
- “needs support” Child lists;
- ranking;
- psychological alerts.

A Child-specific timeline requires intentional navigation and authorization.

## 30. Error privacy

Cross-tenant/unlinked/unassigned resources follow current non-disclosure behavior.

Errors must not reveal:

- another Child has an observation;
- another Parent has feedback;
- hidden methodology draft existence to unauthorized roles.

## 31. Required privacy tests

Future implementation must verify:

1. foreign tenant hidden.
2. unassigned TEACHER denied.
3. inactive assignment/Employee denies next request.
4. unlinked PARENT denied.
5. PARENT response has no internal observation/support tags.
6. ADMIN has no individual observation detail by default.
7. no free-text Child observation field accepted.
8. no diagnosis/score/rank fields exist.
9. browser persistent storage contains no Child development payload.
10. logs/Audit do not contain Child profile text.
11. external specialist/provenance metadata does not grant data access.
12. synthetic-only fixtures.
13. no AI/analytics external data flow.

## 32. Pre-pilot decisions

Before real deployment of Stage 11:

- legal/privacy review of exact observation fields;
- organization policy/purpose;
- staff access policy;
- parent notice/consent requirements where applicable;
- retention/destruction;
- external methodology reviewer relationship;
- training/guidance for teachers to avoid clinical interpretation;
- incident process for inappropriate/sensitive entries;
- hosting/backup controls.

## 33. Acceptance boundary

Technical acceptance proves only that the product enforces the frozen non-medical, non-ranking, minimized-data architecture.

It does not certify a psychological methodology, medical validity, ethical research approval, or full legal compliance.