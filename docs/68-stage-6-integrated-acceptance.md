# Stage 6 — Integrated Technical Acceptance

**Issue:** #152 — S6-ACCEPTANCE  
**Owner:** ONN9IX / Master Chat  
**Acceptance baseline:** `31804ef86449ee14de3cab0fe4aedbbf3e9aeacc`  
**Result:** **PASS — Stage 6 is accepted/frozen when this acceptance record is merged.**

## 1. Scope accepted

Stage 6 is reviewed as one four-role product after:

- DIRECTOR/ADMIN management delivery was merged;
- TEACHER/PARENT delivery Issue #131 / PR #141 was merged;
- the explicit product simplification Issue #150 / PR #151 was merged.

The product-scope simplification is authoritative for the active surface. Deferred modules are preserved in code/models/data but are OFF by default.

## 2. CI evidence

### TEACHER/PARENT final PR

CI run **#204** — SUCCESS, 8/8:

- Backend quality;
- Frontend quality;
- Dependency security;
- Browser auth flow;
- Local browser preview;
- PostgreSQL backup and recovery;
- Backend checks;
- Frontend checks.

### TEACHER/PARENT post-merge

CI run **#205** on merge commit `649ca371ba202651ca4a167e71d8d5380486bb91` — SUCCESS, 8/8.

### Product module flags

CI run **#210** on final PR head `d0e6b7f962ab6579ed83b79ec3c8d41ddd176e3e` — SUCCESS, 8/8.

The resulting active product baseline is:

`31804ef86449ee14de3cab0fe4aedbbf3e9aeacc`

No open Issues or PRs existed immediately before Issue #152 was created.

## 3. Active product modules — ON

### Common/core

- authentication;
- temporary-password change;
- logout/session revocation;
- tenant isolation;
- role-based access;
- account lifecycle.

### DIRECTOR / ADMIN

- Dashboard / Today;
- Children;
- Groups;
- Guardians / Parents;
- Employees;
- Teachers;
- Teacher assignments;
- Attendance;
- Schedule;
- Announcements;
- Tasks;
- Group communications;
- Notifications.

### DIRECTOR-only

- Audit;
- Organization Settings;
- privileged account/assignment actions according to the frozen RBAC contract.

### TEACHER

- Today;
- assigned Groups/roster;
- eligible Guardian context;
- Attendance;
- Schedule;
- Announcements;
- Group/direct communication;
- own Tasks;
- own Notifications.

### PARENT

- linked Children context;
- eligible Announcements;
- Group/direct communication with the server-owned participant boundary.

## 4. Deferred modules — OFF but preserved

These capabilities remain in source/data model where already implemented but are not part of the active product surface:

- Polls;
- Incidents;
- Diary;
- Photos;
- Photo consents;
- Document notices.

OFF semantics are frozen as:

1. hidden from navigation/tabs/cards;
2. direct frontend routes redirect to the role home;
3. corresponding API entry paths return safe `NOT_FOUND`;
4. models/services/data are not deleted;
5. legacy capability regression can explicitly enable the feature flag in tests;
6. re-enabling requires an explicit Master Chat decision and regression validation.

## 5. Future runtime — paused

The following designed future domains are not authorized for runtime implementation until Master Chat explicitly re-enables them:

- Stage 7 Contracts / Billing / Payments / Debt / Receipts;
- Stage 9 Entry Kiosk / entrance tablet;
- Stage 10 production protected-storage rollout while its dependent product modules are OFF;
- Stage 11 psychology-informed Development Support / individual approach;
- Stage 12 SaaS tenant subscription.

Design documentation is retained. No future design is deleted.

## 6. Four-role acceptance

### DIRECTOR — PASS

Accepted boundaries:

- full same-tenant operational management for active core modules;
- teacher account/assignment management under frozen rules;
- Audit read;
- Organization Settings;
- no cross-tenant access;
- no client-owned tenant/actor authority.

### ADMIN — PASS

Accepted boundaries:

- operational management for permitted core modules;
- no Audit;
- no DIRECTOR-only Settings write;
- no privileged account/assignment controls reserved for DIRECTOR;
- tenant isolation preserved.

### TEACHER — PASS

Accepted boundaries:

- active TEACHER identity requires the frozen Employee/session relationship;
- current assignment controls Group/Child access;
- assignment/Employee revocation removes access on subsequent requests;
- Attendance remains the canonical attendance domain;
- schedule/announcements/tasks/notifications/communications are assignment/ownership scoped;
- management-only navigation/actions remain unavailable.

### PARENT — PASS

Accepted boundaries:

- active same-tenant Guardian + ChildGuardian controls linked Child access;
- direct conversation bootstrap uses server-derived participants;
- communication access remains participant-scoped;
- no management/teacher write privileges;
- deferred Diary/Polls/Photos are OFF.

## 7. Tenant and authorization acceptance

PASS:

- tenant is derived only from authenticated User;
- foreign UUIDs cannot establish authority;
- role checks remain server-side;
- TEACHER assignment is revalidated;
- PARENT relation/participant scope is revalidated;
- frontend visibility is never the authorization boundary;
- disabled API modules return non-disclosing `NOT_FOUND`.

## 8. Attendance acceptance

PASS:

- one canonical Attendance domain remains in use;
- management and assigned TEACHER operate on the same records;
- Organization timezone/garden-local date semantics remain active;
- no entrance-kiosk second attendance system exists;
- attendance remains staff-operated in the active product.

## 9. Communications acceptance

PASS:

- Group communication remains available;
- direct TEACHER↔PARENT communication remains participant-scoped;
- PARENT can bootstrap an eligible direct thread from linked Child context;
- sender/actor fields remain server-owned;
- free-text message bodies are not copied into business Audit details.

## 10. Privacy / 152-FZ technical boundary

PASS for the frozen technical contract:

- tenant isolation preserved;
- RBAC preserved;
- assignment/Guardian relation scope preserved;
- synthetic-only dev/test/preview requirement preserved;
- no new speculative PII added by Stage 6 acceptance;
- Audit remains privacy-minimized;
- disabled modules do not expose their data through active UI/API surfaces;
- no medical, biometric or face-recognition functionality is introduced.

This technical acceptance **does not** claim full 152-FZ compliance and **does not** authorize a real-PII production pilot by itself.

## 11. Stage 5 regression gates

PASS through the required Stage 6/product CI evidence:

- dependency security;
- PostgreSQL backup/recovery;
- Docker local preview;
- browser end-to-end;
- backend quality;
- frontend quality;
- backend checks;
- frontend checks.

## 12. Schema

Current migration head:

`0012_stage6_teacher_foundation.py`

No migration is introduced by Issue #152.

## 13. Findings

### BLOCKER

None.

### CURRENT STAGE

None.

### TECH DEBT

- ESLint 9 remains the known compatibility/EOL debt already recorded by the repository.
- Source-of-truth files were stale before Issue #152 and are corrected by this acceptance branch.

### FUTURE / intentionally paused

- contracts/billing;
- entrance kiosk;
- protected production binary storage rollout;
- development-support/psychology;
- SaaS tenant subscription;
- any re-enable of Polls/Incidents/Diary/Photos/Photo consents/Document notices.

## 14. Freeze decision

When this acceptance record and the updated source-of-truth files merge with green required CI:

**Stages 1–6 are FROZEN.**

The frozen active Stage 6 product baseline is:

`31804ef86449ee14de3cab0fe4aedbbf3e9aeacc`

Later documentation-only acceptance commits do not change that product-code baseline.

Any new runtime scope or re-enabled module requires a fresh explicit Master Chat Issue, exact baseline, write-set, tests and CI.
