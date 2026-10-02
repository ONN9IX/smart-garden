# ПРОМАКС — latent OFF modules enable / rollback playbook

Status: **DESIGN / DEFAULT OFF**

Issue: #159

## 1. Objective

Make future activation small, explicit and reversible.

The current product uses static global feature gates in:
- `backend/app/core/product_features.py`;
- `frontend/src/config/product-features.ts`.

This design does **not** introduce tenant-specific flags.

Therefore an activation changes the global product baseline for all tenants/environments using that build.

If per-tenant rollout is required later, stop and design tenant feature configuration separately.

## 2. Activation units

| Unit | Includes | Independent activation? |
|---|---|---|
| `polls` | Polls | Yes |
| `incidents` | Incidents | Yes |
| `diary` | Diary | Yes |
| `photos` | Photos + Photo consents | Yes as one bundled unit |
| `document_notices` | Document notices | Yes |

Photo consent must not be split from Photos in the active product baseline without a new architecture decision.

## 3. What “ready to enable” means

A module is ready when:
- product behavior is frozen;
- RBAC matrix is accepted;
- API scope is accepted;
- frontend route/navigation is known;
- human-readable labels exist;
- default-OFF tests pass;
- ON-mode capability tests pass;
- tenant isolation tests pass;
- privacy review is complete for intended deployment;
- manual acceptance script exists;
- rollback path is verified.

Only then may a delivery Issue set its flags to ON.

## 4. Mechanical activation step

After all gates below pass, the implementation Issue may change the matching feature from `false` to `true` in both product feature registries.

Example conceptual change:

```text
backend PRODUCT_FEATURES["polls"]: false → true
frontend PRODUCT_FEATURES.polls: false → true
```

Never change only one side.

The delivery must include a regression that detects backend/frontend exposure drift.

## 5. Preflight checklist — every module

### Product
- [ ] Still needed in current product scope
- [ ] No conflict with newer UX/IA decisions
- [ ] Russian labels finalized
- [ ] Navigation placement finalized
- [ ] Empty/loading/error states defined

### Security
- [ ] Authentication required
- [ ] Tenant derived only from authenticated User
- [ ] Role checks verified
- [ ] TEACHER assignment scope verified
- [ ] PARENT linked-child scope verified where applicable
- [ ] Foreign UUID behavior non-disclosing
- [ ] Direct API access tested, not only hidden UI

### Privacy
- [ ] Data-minimization reviewed
- [ ] Retention decision exists for real deployment
- [ ] Audit minimization reviewed
- [ ] Notification preview minimization reviewed
- [ ] 152-ФЗ/privacy specialist review completed where required

### Testing
- [ ] Default-OFF API returns safe 404
- [ ] Default-OFF routes/nav hidden
- [ ] Feature-ON backend tests pass
- [ ] Feature-ON frontend tests pass
- [ ] Cross-role negative tests pass
- [ ] Cross-tenant tests pass
- [ ] Manual role acceptance passes

## 6. Module-specific gates

### Polls

Before ON:
- confirm audience rules;
- confirm aggregate-result privacy;
- verify one-vote behavior;
- verify close behavior;
- verify Parent cannot access unrelated group polls;
- verify Teacher cannot create for unassigned group.

Recommended manual E2E:
DIRECTOR/TEACHER create → PARENT sees eligible poll → PARENT votes → creator sees aggregate → close → voting blocked.

### Incidents

Before ON:
- confirm Parent remains unexposed;
- human-readable states;
- exception-first DIRECTOR/ADMIN dashboard behavior;
- free-text minimization guidance;
- no health/psychology expansion.

Manual E2E:
TEACHER assigned group creates → DIRECTOR/ADMIN sees → status changes → foreign Teacher blocked → PARENT cannot access.

### Diary

Before ON:
- concise-entry UX;
- linked-child Parent visibility;
- Teacher assignment scope;
- no psychology/development scoring.

Manual E2E:
TEACHER writes linked child diary → PARENT sees own child → unrelated Parent blocked → unassigned Teacher blocked.

### Photos

Hard dependencies before real-person activation:
- protected storage;
- authenticated content delivery;
- consent state enforcement;
- withdrawal handling;
- retention/destruction decision;
- backup/storage review;
- privacy/legal review.

Manual E2E:
consent valid → assigned Teacher upload → linked Parent sees;
consent absent/withdrawn → upload/publication blocked as designed;
foreign Parent/Teacher blocked.

Synthetic-only preview can be tested earlier, but must not be represented as production readiness.

### Document notices

Before ON:
- acknowledgement wording clearly non-signature;
- recipient targeting verified;
- management completion view;
- no contract/payment semantics.

Manual E2E:
DIRECTOR/ADMIN publish to Teacher → addressed Teacher sees → acknowledges → management sees acknowledged state → unrelated user blocked.

## 7. Automation activation rule

While a module is OFF:
- no user-visible notification from it;
- no dashboard exception from it;
- no background action should expose its existence.

When ON:
- enable only the side effects defined in docs/70;
- do not create new cross-module automation opportunistically in the same activation PR.

This keeps activation small and reviewable.

## 8. Rollback

Rollback goal: restore the module to invisible/inaccessible without destructive data operations.

Procedure:
1. set matching backend feature key to `false`;
2. set matching frontend feature key to `false`;
3. deploy;
4. verify API returns safe 404;
5. verify nav/routes are hidden;
6. verify no latent-module dashboard/notifications leak;
7. preserve stored data pending approved retention/destruction policy.

Do not:
- drop tables;
- delete migrations;
- purge production data as part of emergency feature-off;
- bypass normal retention/privacy procedures.

## 9. PR scope for a future activation

Default preferred activation Issue:
- one module/activation unit;
- one fresh branch;
- feature-gate changes;
- only UI polish strictly necessary for exposure;
- targeted ON/OFF tests;
- manual E2E checklist;
- no unrelated architecture work.

Photos may be larger because protected-storage prerequisites can make it an infrastructure/privacy delivery rather than a simple toggle.

## 10. CI acceptance

Future activation PR must keep all existing required CI green and add/retain targeted evidence for:
- OFF boundary;
- ON behavior;
- RBAC;
- tenant isolation;
- browser exposure;
- rollback safety.

## 11. Freeze decision

Until a specific activation Issue is explicitly authorized:

```text
polls = OFF
incidents = OFF
diary = OFF
photos + photo consents = OFF
document notices = OFF
```

The existence of this design is **not authorization to enable any module**.
