# ПРОМАКС — latent OFF modules data and privacy contract

Status: **DESIGN / DEFAULT OFF**

Issue: #159

## 1. Scope

This document defines privacy/data boundaries for:
- Polls;
- Incidents;
- Diary;
- Photos;
- Photo consents;
- Document notices.

It is a technical/product privacy baseline, not a claim of complete 152-ФЗ compliance.

Real-pilot legal/privacy prerequisites from the current project state remain unresolved and must be completed separately.

## 2. Global privacy rules

1. Tenant isolation is mandatory.
2. Collect only data necessary for the defined product purpose.
3. Do not add speculative fields during activation.
4. Dev/test/preview uses synthetic data only.
5. OFF does not mean deleted; existing retained data remains subject to retention/destruction rules.
6. Disabling a module is not a lawful deletion workflow.
7. Access must be purpose- and role-limited.
8. Audit details must be minimized and must not duplicate sensitive content unnecessarily.
9. Free-text fields require stronger minimization because users can enter excess personal data.
10. No latent module may silently become a psychology, medical, biometric or legal-signature system.

## 3. Data classification by module

### Polls

Expected data:
- tenant;
- audience/group;
- question;
- options;
- state;
- eligible/voting relationship;
- aggregate counts;
- timestamps.

Privacy default:
- do not display individual Parent votes;
- do not use polls to collect sensitive personal data;
- do not use poll responses as consent for photos/contracts/processing unless a separate legally reviewed workflow explicitly defines that purpose.

Recommended UI warning for poll authors:
- avoid requesting unnecessary personal/sensitive information in free text.

### Incidents

Expected data:
- tenant;
- group/child reference when necessary;
- factual operational description;
- status;
- author/responsible staff;
- timestamps.

High-risk behavior to prevent:
- medical diagnosis;
- detailed health history;
- psychological labels;
- subjective profiling;
- unrelated family information.

Design principle:
**record the operational event, not a dossier about the child.**

If the product later needs health/medical information, that requires a separate data/privacy architecture decision.

### Diary

Expected data:
- tenant;
- child;
- date;
- short note;
- author;
- timestamps.

Risk:
free text can drift into sensitive profiling.

Controls:
- concise UI;
- no hidden score;
- no behavioral ranking;
- no diagnosis;
- no psychology-development conclusions;
- linked-parent visibility only for their child;
- TEACHER assignment scope.

### Photos

Expected data:
- tenant;
- group;
- child associations where applicable;
- file metadata;
- protected object/content;
- uploader;
- timestamps;
- eligibility context.

Rules:
- no public-by-default access;
- no cross-tenant URLs;
- no permanent public sharing link;
- no external social sharing workflow;
- no face recognition;
- no biometric identification;
- no ML-training use.

A normal photograph must not be repurposed into biometric processing without a separate explicit architecture/legal decision.

### Photo consents

Expected data:
- tenant;
- child;
- guardian/authorized basis according to frozen model;
- consent state;
- scope;
- timestamps;
- withdrawal state.

Rules:
- withdrawal must be visible to authorized staff;
- upload/publication eligibility must use current consent state;
- historical audit may preserve that a state transition occurred without retaining unnecessary sensitive content;
- activation requires a defined retention/destruction policy and protected storage appropriate to the real deployment.

### Document notices

Expected data:
- tenant;
- notice body/title;
- authorized recipients/audience;
- created timestamp;
- acknowledgement state/time;
- actor.

Rules:
- acknowledgement is an application event only;
- do not label it as legal signature;
- do not attach contract/payment semantics;
- avoid placing passports, payment details or unrelated sensitive documents in this module.

## 4. Role privacy boundaries

### DIRECTOR

Broadest tenant operational visibility, but still:
- no cross-tenant access;
- no unnecessary sensitive-data duplication;
- no assumption that Director may expose data to unauthorized recipients.

### ADMIN

Operational access only according to existing RBAC.
Activation must not use latent modules to grant ADMIN Director-only security powers.

### TEACHER

Assignment-scoped.
The teacher must not browse:
- foreign groups;
- foreign children;
- foreign guardian data;
- photos/diary/incidents outside assignment.

### PARENT

Guardian/ChildGuardian-scoped.
The parent must not browse:
- other children;
- other parents' identities or poll votes;
- unrelated group photos;
- staff-only incidents;
- management notice metadata.

## 5. Retention and deletion

Before real-pilot activation, each module needs a deployment-specific retention decision.

At minimum define:
- business retention period;
- legal basis/purpose;
- who can archive/delete where deletion is supported;
- backup retention interaction;
- effect of guardian/child relationship termination;
- effect of employee departure;
- photo withdrawal handling;
- audit retention.

Do not invent retention periods in code without an approved policy.

## 6. Audit minimization

Audit should record:
- actor;
- action type;
- target identifier/type;
- timestamp;
- minimal scope/context.

Audit should not copy:
- full incident narrative;
- diary text;
- photo bytes;
- full notice body;
- poll free text unnecessarily.

## 7. Notifications minimization

Lock-screen/push style notifications must not expose unnecessary child-sensitive content.

Preferred:
- «Новое сообщение/обновление в ПРОМАКС»
- «Новое извещение»
- «Требуется действие в группе»

Avoid:
- detailed incident narrative;
- sensitive diary content;
- private child information in notification preview.

## 8. Photo storage activation gate

The `photos` feature must remain OFF for real-person photo use until the relevant deployment has resolved:
- protected storage;
- authenticated content delivery;
- authorization on every content fetch;
- backup protection/location/retention;
- operational access administration/revocation;
- retention/destruction;
- legal/privacy specialist review.

Synthetic-only preview data does not satisfy production requirements.

## 9. 152-ФЗ activation review

Before enabling any latent module with real personal data, the activation Issue must explicitly review:
- purpose and necessity;
- data categories;
- subjects and recipients;
- operator/controller/processor responsibilities as applicable;
- localization/hosting/subprocessors as applicable;
- access controls;
- retention/destruction;
- incident response;
- user-facing notices/consents where applicable.

This project document is an engineering guardrail, not legal advice or a production compliance certificate.
