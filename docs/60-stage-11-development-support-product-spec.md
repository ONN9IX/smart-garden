# Stage 11 — Development Support Product Specification

**Status:** design proposal for Issue #146; frozen only after the design PR merges.
**Owner:** ONN9IX.
**Implementation:** NOT AUTHORIZED until Stage 6 integrated acceptance is complete.
**Design baseline:** `7a37789a5fb24334cb245bd251b5f4b0eb18657a`.

## 1. Goal

Add a psychology-informed but strictly non-medical development-support vertical to Smart Garden.

The product should help a kindergarten:

- use reviewed development activities;
- plan them for Groups/Children;
- record bounded activity outcomes;
- give parents clear home recommendations;
- collaborate with a psychology department on methodology quality;

without turning Smart Garden into a diagnostic, medical, psychometric or child-ranking platform.

## 2. Core product flow

```text
methodology draft
→ review/provenance
→ publish immutable version
→ TEACHER assigns activity
→ Child participates
→ TEACHER records structured outcome
→ optional approved parent recommendation
→ PARENT completes/acknowledges home activity
→ operational aggregate usage
```

## 3. Non-medical boundary

Stage 11 core does not provide:

- diagnosis;
- clinical psychological assessment;
- treatment plan;
- medication;
- medical note;
- disorder/syndrome label;
- mental-health risk score;
- developmental “normal/abnormal” verdict;
- percentile;
- IQ/cognitive-test interpretation;
- automated concern flag;
- AI diagnosis/recommendation;
- emotion/face recognition.

If staff has a concern requiring specialist or medical handling, Smart Garden points to the organization's approved offline process rather than storing a clinical conclusion.

## 4. Roles

### DIRECTOR

May:

- create/edit methodology drafts;
- approve/publish/archive methodology versions;
- view methodology provenance;
- view organization/Group usage aggregates;
- view individual development activity history only where business oversight is justified;
- view relevant Audit.

DIRECTOR does not receive diagnostic tools because none exist.

### ADMIN

May:

- manage methodology drafts/metadata;
- schedule/coordinate approved activities;
- view operational counts/statuses.

ADMIN does not receive detailed individual observation outcomes by default.

### TEACHER

May, only for currently assigned active Groups/Children:

- browse published methodology;
- plan/assign approved activities;
- mark activity completion;
- record structured activity outcome;
- record bounded support tags;
- create/publish a parent-facing recommendation from an approved methodology version;
- view the assigned Child's internal activity timeline.

TEACHER cannot create diagnoses, numeric scores or child rankings.

### PARENT

May, only for actively linked Child:

- read published parent recommendations/home activities;
- read methodology purpose/steps/materials intended for parent;
- submit bounded completion feedback.

PARENT does not read the internal teacher observation outcome by default.

## 5. No new specialist role in core

Stage 11 core does not add PSYCHOLOGIST/SPECIALIST to User.role.

Reason:

- current auth/RBAC has four frozen roles;
- adding another role changes shared auth/navigation/permissions;
- external university/department specialists do not need tenant access merely to curate methodology.

A future in-app specialist role requires a separate explicit design and migration/auth gate.

## 6. Psychology department collaboration

Stage 11 supports methodology provenance without creating external tenant accounts.

A methodology version may include:

- source organization/reference;
- source title/reference;
- review organization;
- reviewed_at;
- methodology version label;
- publication status.

Prefer organization-level provenance, for example a department/laboratory name, instead of unnecessary personal reviewer identity.

This lets Smart Garden present reviewed methodology packs while keeping production access controlled by the kindergarten.

## 7. Methodology identity

Use a stable MethodologyItem identity and immutable published MethodologyVersion records.

MethodologyItem:

- stable UUID;
- tenant;
- short title;
- domain tags;
- lifecycle.

MethodologyVersion:

- version number;
- purpose;
- age band;
- duration;
- materials;
- structured steps;
- parent/home variant if applicable;
- source/reference;
- review metadata;
- status;
- created/published timestamps.

## 8. Methodology lifecycle

Suggested states:

- `draft`
- `under_review`
- `published`
- `archived`

Rules:

- draft can change;
- under_review is not selectable for ordinary activity use;
- published version is immutable;
- edits to published methodology create a new draft/version;
- archived version remains referenced by historical activity records.

## 9. Development domains

Use neutral activity-organization tags, not diagnoses.

Initial conceptual tags:

- `communication`
- `cooperation`
- `attention_in_activity`
- `self_regulation_in_activity`
- `independence`
- `motor_coordination`
- `creativity_problem_solving`

These tags describe the purpose of an activity, not a Child condition.

No tag means “disorder”, “delay”, “risk” or “abnormal”.

## 10. Age bands

Methodology may have a broad target age band.

Age band is guidance for staff selection, not an automatic developmental norm.

The system must not conclude that a Child is behind/ahead merely because an activity is associated with another age band.

## 11. Activity planning

TEACHER or authorized management may create a DevelopmentActivity from a published MethodologyVersion.

Target:

- one active Group; or
- one active Child in an authorized Group.

Fields conceptually include:

- methodology_version_id;
- group_id;
- optional child_id;
- planned_on;
- status;
- created_by.

No medical purpose/reason field.

## 12. Activity lifecycle

Suggested states:

- `planned`
- `completed`
- `cancelled`

A Group-targeted activity can produce one structured observation per participating Child.

A Child-targeted activity applies only to that Child.

Historical records remain linked to the immutable methodology version used at the time.

## 13. Structured teacher observation

Observation describes the Child's participation in **that activity only**.

Outcome enum:

- `participated`
- `completed_with_support`
- `completed_independently`
- `not_observed`

No numeric score.

No “failed”.

No “below norm”.

No free-text clinical/psychological profile.

## 14. Support tags

Optional bounded tags describe what assistance occurred during the activity:

- `verbal_prompt`
- `demonstration`
- `repetition`
- `peer_support`

Support tags are not diagnostic traits.

Do not aggregate them into a risk score.

## 15. No child observation free text in core

Stage 11 core deliberately excludes an unrestricted teacher free-text field attached to the Child observation.

Reason:

- free text can accidentally contain health/diagnostic/sensitive claims;
- structured activity outcome is sufficient for MVP;
- a future note field would need purpose, visibility, retention and privacy review.

Methodology instructions themselves can contain normal educational text because they do not describe a specific Child.

## 16. Internal Child activity timeline

TEACHER for assigned Child and DIRECTOR where authorized may view a chronological timeline of:

- activity;
- date;
- methodology version;
- structured outcome;
- support tags.

The timeline does not calculate:

- average score;
- percentile;
- risk;
- predicted development;
- comparison with other Children.

## 17. Parent recommendation

A TEACHER may create a PARENT-facing recommendation from a published MethodologyVersion/home variant.

Fields conceptually:

- child_id;
- methodology_version_id;
- title/purpose derived from approved version;
- published_at;
- optional due_on;
- status.

Recommendation text should reuse approved methodology rather than ad-hoc psychological profiling.

## 18. Parent visibility

PARENT receives only recommendations for actively linked Children.

PARENT sees:

- activity title;
- educational purpose;
- materials;
- home steps;
- date/status.

PARENT does **not** see by default:

- internal outcome;
- internal support tags;
- another Child;
- Group analytics;
- methodology drafts/review notes.

## 19. Parent feedback

Core parent feedback is bounded.

Suggested status:

- `completed`
- `skipped`
- `needs_clarification`

One authenticated PARENT may submit/update their own feedback according to the frozen rule.

No free-text psychological assessment from PARENT in core.

## 20. Multiple Guardians

Ordinary recommendation visibility follows active ChildGuardian relation.

Each eligible PARENT User may have their own feedback row/state if required.

Do not reveal one Guardian's private account metadata to another Guardian.

The product may show an aggregate “completed by family” state only if the implementation contract explicitly defines it without exposing another Guardian identity.

## 21. Management analytics

Allowed operational analytics:

- activities planned/completed by Group;
- methodology version usage counts;
- recommendation publication count;
- parent completion-status counts;
- methodology adoption over time.

Do not produce child rankings or cross-child outcome leaderboards.

## 22. Teacher analytics

TEACHER may see operational activity completion for assigned Group.

Do not show:

- “top/bottom children”;
- comparative outcome ranking;
- normalized developmental score.

The useful unit is “what activity remains to be done”, not “which Child is worst”.

## 23. Director dashboard boundary

Stage 11 may later add attention cards such as:

- activities planned this week;
- unpublished methodology drafts;
- recommendations awaiting parent action count.

Do not place Child-level outcomes on the general management Dashboard.

## 24. Search/filter

Methodology filters may use:

- published status;
- age band;
- domain tag;
- source/review organization.

Development activity filters may use:

- Group;
- planned date;
- status.

Avoid free-text search over Child observation data because the core has no free-text Child observation.

## 25. Notifications

Minimal notifications may be created for:

- new parent recommendation;
- recommendation updated/archived;
- methodology publication for relevant staff if useful.

Notification body does not contain Child observation outcome.

External push/email/SMS remains subject to provider privacy review.

## 26. Audit

Required domain actions include:

- methodology create/version;
- methodology submit/review-status transition;
- methodology publish/archive;
- development activity create/cancel/complete;
- observation record/update;
- parent recommendation publish/archive;
- parent feedback create/update.

Audit details contain IDs, statuses and changed field names only.

No diagnosis exists to log.

## 27. No AI in Stage 11 core

Do not use AI to:

- classify Child behavior;
- infer diagnosis;
- generate risk;
- suggest medical/psychological treatment;
- rank Children;
- summarize private Child development data externally.

A future AI assistant for methodology authoring could be considered separately using non-PII content only.

## 28. No biometrics/emotion recognition

Photos/video/audio are not analyzed to infer:

- emotion;
- attention;
- stress;
- personality;
- development.

Stage 11 observations are intentional staff-entered activity records only.

## 29. Product acceptance target

Future technical acceptance should demonstrate:

```text
DIRECTOR
→ draft methodology
→ review metadata
→ publish immutable version

TEACHER assigned to Group
→ choose published activity
→ plan for Child/Group
→ record bounded outcome/support
→ publish parent recommendation

PARENT linked to Child
→ read recommendation
→ submit bounded feedback

unassigned TEACHER / unrelated PARENT / foreign tenant
→ denied

no screen/API
→ diagnosis, score, ranking, free-text Child psychological profile
```

## 30. Value proposition

Stage 11 differentiates Smart Garden by connecting daily kindergarten operations with a curated development methodology layer while keeping a strict boundary between educational support and clinical psychology.

It creates a collaboration surface for psychology experts without requiring the product to make medical claims.