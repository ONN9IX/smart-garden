# Stage 11 — Development Support Permissions and API

**Status:** design proposal for Issue #146; frozen only after the design PR merges.
**Owner:** ONN9IX.
**Implementation:** NOT AUTHORIZED until Stage 6 integrated acceptance is complete.
**Conventions:** /api/v1, JSON snake_case, UUID identifiers, server-owned tenant/actor fields.

## 1. Authorization invariants

1. Tenant is derived only from authenticated User.
2. PARENT child access requires an active same-tenant ChildGuardian relation.
3. TEACHER child/group access requires current active assignment under frozen Stage 6 rules.
4. Client-supplied organization_id, actor, author or owner never grants authority.
5. Methodology publication is management-controlled.
6. Published methodology is immutable.
7. No route accepts a diagnosis, score, percentile or unrestricted Child observation text.
8. Frontend visibility is not authorization.

## 2. Permission matrix

| Capability | DIRECTOR | ADMIN | TEACHER | PARENT |
|---|---|---|---|---|
| Read published methodology | Yes | Yes | Yes | Parent-facing version only where recommended |
| Create/edit methodology draft | Yes | Yes | No | No |
| Submit methodology for review | Yes | Yes | No | No |
| Publish/archive methodology version | Yes | No | No | No |
| Read methodology provenance | Yes | Yes | Yes | Public/parent-safe subset only |
| Create DevelopmentActivity | Yes | Yes | Assigned Group/Child only | No |
| Cancel DevelopmentActivity | Yes | Yes | Own/assigned scope | No |
| Record Child observation | No ordinary workflow | No | Assigned Group/Child only | No |
| Read individual internal observation | Yes where justified | No by default | Assigned Child only | No |
| Publish ParentRecommendation | Yes | Yes if operationally authorized | Assigned Child only | No |
| Read ParentRecommendation | management | operational | assigned Child | linked Child only |
| Submit ParentFeedback | No | No | No | own eligible recommendation |
| View aggregate usage analytics | Yes | Yes | assigned Group only | No |
| View child ranking/score | Not available | Not available | Not available | Not available |

## 3. Proposed data model

This document freezes semantics, not ORM implementation details.

### MethodologyItem

- id: UUID
- organization_id: UUID
- title: string
- status: active | archived
- created_by: UUID
- created_at
- updated_at

### MethodologyVersion

- id: UUID
- methodology_item_id: UUID
- version_number: integer
- status: draft | under_review | published | archived
- purpose: string
- age_band_code: string/enum
- duration_minutes: integer | null
- materials: structured list/text with bounded size
- steps: structured ordered list
- parent_variant: structured optional content
- domain_tags: bounded enum list
- source_reference: string | null
- source_organization: string | null
- review_organization: string | null
- reviewed_at: timestamp | null
- created_by: UUID
- created_at
- published_at: timestamp | null

Published versions are immutable.

### DevelopmentActivity

- id: UUID
- organization_id: UUID
- methodology_version_id: UUID
- group_id: UUID
- child_id: UUID | null
- planned_on: date
- status: planned | completed | cancelled
- created_by: UUID
- created_at
- completed_at: timestamp | null

Rules:

- methodology version must be published;
- Group is active and same tenant;
- optional Child must be active, same tenant and currently in the Group at creation;
- TEACHER must be assigned to Group.

### DevelopmentObservation

- id: UUID
- organization_id: UUID
- activity_id: UUID
- child_id: UUID
- outcome: participated | completed_with_support | completed_independently | not_observed
- support_tags: bounded enum list
- recorded_by: UUID
- recorded_at
- updated_at

No numeric score.
No free-text Child profile.

### ParentRecommendation

- id: UUID
- organization_id: UUID
- child_id: UUID
- methodology_version_id: UUID
- source_activity_id: UUID | null
- published_by: UUID
- published_at
- due_on: date | null
- status: active | archived

The recommendation uses approved parent-facing methodology content rather than storing an ad-hoc psychological profile.

### ParentFeedback

- id: UUID
- organization_id: UUID
- recommendation_id: UUID
- guardian_id: UUID
- status: completed | skipped | needs_clarification
- updated_at

Unique per recommendation + eligible Guardian where this model is used.

No free-text assessment in core.

## 4. Methodology API

Management routes:

- GET /api/v1/development/methodologies
- POST /api/v1/development/methodologies
- GET /api/v1/development/methodologies/{methodology_id}
- POST /api/v1/development/methodologies/{methodology_id}/versions
- GET /api/v1/development/methodologies/{methodology_id}/versions
- PATCH /api/v1/development/methodologies/{methodology_id}/versions/{version_id}
- POST /api/v1/development/methodologies/{methodology_id}/versions/{version_id}/submit-review
- POST /api/v1/development/methodologies/{methodology_id}/versions/{version_id}/publish
- POST /api/v1/development/methodologies/{methodology_id}/versions/{version_id}/archive

DIRECTOR-only:

- publish;
- archive published version.

ADMIN may prepare drafts and review metadata but does not publish.

TEACHER reads published versions through a read-only teacher route or filtered shared read route.

## 5. Published immutability

Generic PATCH is allowed only while a version is draft/under_review under exact management rules.

After publish:

- content fields cannot change;
- corrections create a new version;
- historical DevelopmentActivity keeps old version reference;
- archive changes lifecycle visibility, not historical content.

## 6. Teacher methodology read

Proposed:

- GET /api/v1/teacher/development/methodologies
- GET /api/v1/teacher/development/methodologies/{version_id}

Return published versions only.

No draft/review-only content.

No reviewer personal data beyond approved provenance fields.

## 7. Activity API

Management:

- GET /api/v1/development/activities
- POST /api/v1/development/activities
- GET /api/v1/development/activities/{activity_id}
- POST /api/v1/development/activities/{activity_id}/cancel

Teacher:

- GET /api/v1/teacher/development/activities
- POST /api/v1/teacher/development/activities
- GET /api/v1/teacher/development/activities/{activity_id}
- POST /api/v1/teacher/development/activities/{activity_id}/cancel
- POST /api/v1/teacher/development/activities/{activity_id}/complete

TEACHER routes always revalidate assignment.

## 8. Observation API

Teacher only:

- GET /api/v1/teacher/development/activities/{activity_id}/observations
- PUT /api/v1/teacher/development/activities/{activity_id}/children/{child_id}/observation

PUT is idempotent for one activity/Child observation.

Allowed payload:

- outcome enum;
- support_tags enum list.

Rejected fields include:

- score;
- percentile;
- diagnosis;
- risk;
- note;
- psychological_profile;
- medical_reason.

Unknown extra fields should be rejected by strict schemas.

## 9. Observation authorization

Before read/write, Backend proves:

1. actor is TEACHER;
2. active Employee;
3. active TeacherGroupAssignment;
4. activity belongs to assigned active Group;
5. Child belongs to the activity target:
   - exact Child for child-targeted activity; or
   - active eligible Group Child for group-targeted activity;
6. same tenant.

A past observation remains historical data, but new edits after assignment loss are denied unless a future correction role is explicitly designed.

## 10. Management individual observation access

DIRECTOR may access individual internal observation history only through an explicit same-tenant management route intended for operational oversight.

ADMIN does not receive this detail by default.

Proposed DIRECTOR-only:

- GET /api/v1/development/children/{child_id}/observations

The ordinary management dashboard receives only aggregate counts.

## 11. Parent recommendation API

Teacher:

- POST /api/v1/teacher/development/recommendations
- GET /api/v1/teacher/development/recommendations
- POST /api/v1/teacher/development/recommendations/{recommendation_id}/archive

Management may have equivalent operational routes under development namespace according to the role matrix.

Creation requires:

- published MethodologyVersion with parent_variant;
- active eligible Child;
- assignment for TEACHER;
- tenant match.

Do not accept arbitrary parent-facing psychological free text.

## 12. Parent API

Proposed:

- GET /api/v1/parent/development/recommendations
- GET /api/v1/parent/development/recommendations/{recommendation_id}
- PUT /api/v1/parent/development/recommendations/{recommendation_id}/feedback

Backend derives Guardian from authenticated PARENT.

Recommendation is visible only for an actively linked Child.

Parent response returns only parent-safe methodology fields and the current Guardian's own feedback.

## 13. Parent content minimization

PARENT response may contain:

- recommendation id;
- Child minimal presentation;
- title;
- purpose;
- parent materials;
- parent steps;
- published_at;
- due_on;
- status;
- own feedback.

It must not contain:

- internal DevelopmentObservation;
- support_tags;
- another Guardian's feedback identity;
- Group-level analytics;
- draft methodology;
- review/internal notes.

## 14. Analytics API

Management aggregate endpoints may expose:

- methodology usage count;
- planned/completed activity count;
- recommendation status counts;
- parent feedback status counts.

Teacher aggregates are limited to currently assigned Groups.

No endpoint supports:

- sort Children by outcome;
- rank;
- score;
- percentile;
- prediction;
- risk list.

If a requested analytic would produce a child comparison/ranking, it is outside Stage 11 core.

## 15. Date/time

Planned activity date uses Organization.timezone for garden-local calendar semantics.

Recorded/published timestamps are timezone-aware instants and displayed in garden-local time.

Client cannot change tenant/timezone authority.

## 16. Audit actions

At minimum:

- development.methodology_created
- development.methodology_version_created
- development.methodology_review_submitted
- development.methodology_published
- development.methodology_archived
- development.activity_created
- development.activity_cancelled
- development.activity_completed
- development.observation_recorded
- development.observation_updated
- development.recommendation_published
- development.recommendation_archived
- development.parent_feedback_updated

Audit details may include:

- target UUIDs;
- methodology version;
- status_before/status_after;
- changed field names;
- bounded outcome enum where accountability requires it.

Do not include:

- child name;
- parent name/contact;
- recommendation body;
- methodology instructional text;
- medical/diagnostic content;
- unrestricted notes.

## 17. Error semantics

Use current API envelope and non-disclosure rules.

Examples:

- foreign/hidden Child → current hidden-resource behavior;
- unassigned TEACHER → hidden-resource behavior;
- unpublished methodology selected → stable business error;
- attempt to mutate published version → 409 immutable-state error;
- unsupported observation field → 422 validation;
- PARENT accessing internal observation → denied/route absent.

## 18. No bulk child export

Stage 11 does not provide an endpoint that exports all Child observations for analytics/AI.

Management list endpoints are paginated and purpose-bound.

Any future research export requires a separate legal/privacy/research-governance design.

## 19. Required backend negative tests

Tenant:

- foreign methodology/activity/Child/recommendation hidden;
- forged organization_id rejected/ignored.

Teacher:

- unassigned Group denied;
- inactive assignment denied;
- inactive Employee denied;
- foreign Child denied;
- Child moved from Group cannot receive new observation through stale assignment.

Parent:

- unlinked Child recommendation denied;
- inactive ChildGuardian relation revokes access;
- another Guardian feedback identity not exposed;
- internal observation route denied.

Data boundary:

- score rejected;
- percentile rejected;
- diagnosis rejected;
- risk field rejected;
- observation note/free text rejected;
- unsupported support tag rejected;
- unpublished methodology cannot be assigned.

Lifecycle:

- published methodology immutable;
- old version remains readable for history;
- archived methodology not selectable for new activity under implementation rules.

## 20. Required browser flows

DIRECTOR:

- methodology draft;
- review metadata;
- publish;
- view aggregate usage.

TEACHER:

- browse published methodology;
- plan activity;
- record structured outcomes;
- complete activity;
- publish parent recommendation.

PARENT:

- open recommendation for linked Child;
- read approved home activity;
- submit bounded feedback.

Negative browser assertions:

- no score/rank/diagnosis controls;
- PARENT cannot see internal observation;
- unassigned TEACHER cannot reach another Group/Child.

## 21. Compatibility

Stage 11 must preserve:

- current four-role auth;
- tenant isolation;
- Stage 6 TEACHER assignment rules;
- Stage 8 PARENT ChildGuardian rules;
- privacy-safe Audit;
- synthetic-only dev/test/preview.

No new specialist role is introduced by Stage 11 core.