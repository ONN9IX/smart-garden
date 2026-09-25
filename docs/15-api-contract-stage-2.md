# API Contract — Stage 2

**Проект:** Умный сад  
**Base path:** `/api/v1`  
**Статус:** source of truth для Stage 2 network contract  
**Предыдущий контракт:** `docs/03-api-contract-v0.1.md` сохраняется для Stage 1 auth; этот документ расширяет его.

Любое изменение endpoint/request/response/error code после начала кода требует синхронного изменения Backend, Frontend и Issues.

---

# 1. Roles

Stage 2 public role values:

```text
DIRECTOR
ADMIN
PARENT
```

`TEACHER` и `SUPER_ADMIN` не активируются.

---

# 2. Auth changes

Существующие endpoints сохраняются:

```text
POST /auth/login
GET  /auth/me
POST /auth/change-password
POST /auth/logout
```

AuthResponse теперь допускает:

```json
{
  "user": {
    "id": "uuid",
    "username": "parent-k4m8r2q9",
    "role": "PARENT",
    "status": "active",
    "must_change_password": false
  },
  "organization": {
    "id": "uuid",
    "name": "Детский сад «Солнышко»"
  }
}
```

PARENT может использовать только auth lifecycle и технический Parent screen Stage 2.

Management API для PARENT → 403 `FORBIDDEN`.

---

# 3. Common error

Без изменений:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Проверьте введённые данные",
    "field": "name"
  }
}
```

Правила:
- `message` безопасное и не содержит internal details;
- `field` string или null;
- DB errors/SQL/stack trace клиенту не возвращаются.

---

# 4. HTTP status policy

```text
200 success/update/action
201 resource created
400 validation/business invalid input
401 unauthenticated
403 authenticated but forbidden/blocked
404 not found OR hidden foreign-tenant resource
409 conflict/current state prevents action
500 unexpected
```

FastAPI 422 наружу не используется.

---

# 5. Common resource status

Для Group / Child / Guardian / ChildGuardian:

```text
active
archived
```

List filter:

```text
status=active
status=archived
status=all
```

Default:

```text
status=active
```

---

# 6. Common 404 behavior

Business entity другого tenant не раскрывается.

Ответ:

```http
404
```

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Запись не найдена",
    "field": null
  }
}
```

Нельзя возвращать:
- имя чужой organization;
- тип чужой сущности сверх запрошенного route;
- `FORBIDDEN` с пояснением «другой сад».

---

# 7. Group object

```json
{
  "id": "uuid",
  "name": "Ромашка",
  "status": "active",
  "archived_at": null,
  "created_at": "2026-09-25T12:00:00Z",
  "updated_at": "2026-09-25T12:00:00Z"
}
```

`organization_id` наружу в обычном Group response не нужен.

---

# 8. GET /groups

Role:
- DIRECTOR;
- ADMIN.

Query:

```text
status=active|archived|all
```

Response 200:

```json
{
  "items": [
    {
      "id": "uuid",
      "name": "Ромашка",
      "status": "active",
      "archived_at": null,
      "created_at": "2026-09-25T12:00:00Z",
      "updated_at": "2026-09-25T12:00:00Z"
    }
  ]
}
```

---

# 9. POST /groups

Request:

```json
{
  "name": "Ромашка"
}
```

Success:
- HTTP 201;
- Group object.

Errors:

```text
400 VALIDATION_ERROR
409 GROUP_NAME_CONFLICT
403 FORBIDDEN
```

Client не отправляет `organization_id`.

---

# 10. GET /groups/{group_id}

Success:
- HTTP 200;
- Group object.

Errors:

```text
404 NOT_FOUND
403 FORBIDDEN
```

---

# 11. PATCH /groups/{group_id}

Request:

```json
{
  "name": "Ромашка 2"
}
```

At least one documented update field required.

Success:
- 200 Group object.

Errors:

```text
400 VALIDATION_ERROR
404 NOT_FOUND
409 GROUP_NAME_CONFLICT
```

---

# 12. POST /groups/{group_id}/archive

Body отсутствует.

Success:
- 200 Group object with `status=archived`.

Errors:

```text
404 NOT_FOUND
409 GROUP_NOT_EMPTY
```

---

# 13. POST /groups/{group_id}/restore

Body отсутствует.

Success:
- 200 Group object active.

Errors:

```text
404 NOT_FOUND
409 GROUP_NAME_CONFLICT
```

---

# 14. Child summary

```json
{
  "id": "uuid",
  "first_name": "София",
  "last_name": "Иванова",
  "middle_name": null,
  "birth_date": "2021-05-10",
  "status": "active",
  "group": {
    "id": "uuid",
    "name": "Ромашка",
    "status": "active"
  }
}
```

---

# 15. Guardian summary

```json
{
  "id": "uuid",
  "first_name": "Анна",
  "last_name": "Иванова",
  "middle_name": null,
  "phone": "+79990000000",
  "email": "anna@example.test",
  "status": "active"
}
```

phone/email могут быть null.

---

# 16. ChildGuardian object

```json
{
  "id": "uuid",
  "relation_type": "mother",
  "status": "active",
  "guardian": {
    "id": "uuid",
    "first_name": "Анна",
    "last_name": "Иванова",
    "middle_name": null,
    "phone": "+79990000000",
    "email": "anna@example.test",
    "status": "active"
  },
  "archived_at": null,
  "created_at": "2026-09-25T12:00:00Z",
  "updated_at": "2026-09-25T12:00:00Z"
}
```

relation_type:

```text
mother
father
legal_guardian
other
```

---

# 17. Child detail

```json
{
  "id": "uuid",
  "first_name": "София",
  "last_name": "Иванова",
  "middle_name": null,
  "birth_date": "2021-05-10",
  "status": "active",
  "group": {
    "id": "uuid",
    "name": "Ромашка",
    "status": "active"
  },
  "guardians": [],
  "archived_at": null,
  "created_at": "2026-09-25T12:00:00Z",
  "updated_at": "2026-09-25T12:00:00Z"
}
```

---

# 18. GET /children

Role:
- DIRECTOR;
- ADMIN.

Query:

```text
status=active|archived|all
group_id=UUID optional
q=string optional
```

`q` searches ФИО case-insensitive.

Response:

```json
{
  "items": []
}
```

Each item = Child summary.

Foreign tenant `group_id` must not expose existence; request returns 404 `NOT_FOUND`.

---

# 19. POST /children

Request:

```json
{
  "group_id": "uuid",
  "first_name": "София",
  "last_name": "Иванова",
  "middle_name": null,
  "birth_date": "2021-05-10"
}
```

Success:
- 201 Child detail.

Errors:

```text
400 VALIDATION_ERROR
400 INVALID_BIRTH_DATE
404 NOT_FOUND
409 GROUP_ARCHIVED
```

`organization_id` отсутствует.

---

# 20. GET /children/{child_id}

Success:
- 200 Child detail.

Errors:
- 404 NOT_FOUND.

---

# 21. PATCH /children/{child_id}

Request may contain any subset:

```json
{
  "group_id": "uuid",
  "first_name": "София",
  "last_name": "Иванова",
  "middle_name": null,
  "birth_date": "2021-05-10"
}
```

Rules:
- omitted field = unchanged;
- `middle_name: null` clears middle name;
- at least one field required.

Success:
- 200 Child detail.

Errors:

```text
400 VALIDATION_ERROR
400 INVALID_BIRTH_DATE
404 NOT_FOUND
409 GROUP_ARCHIVED
```

---

# 22. POST /children/{child_id}/archive

Success:
- 200 Child detail with archived status.

Active Guardian relations are retained as historical/current links; physical rows are not deleted.

---

# 23. POST /children/{child_id}/restore

Restore uses existing `group_id`.

Success:
- 200 Child detail.

Errors:

```text
404 NOT_FOUND
409 GROUP_ARCHIVED
```

If former Group archived, user must restore Group or update Child to an active Group as permitted by Backend workflow.

---

# 24. ParentAccountSummary

```json
{
  "id": "uuid",
  "username": "parent-k4m8r2q9",
  "status": "active",
  "must_change_password": true
}
```

No password/hash/session fields.

---

# 25. Guardian child relation summary

```json
{
  "relation_id": "uuid",
  "relation_type": "mother",
  "relation_status": "active",
  "child": {
    "id": "uuid",
    "first_name": "София",
    "last_name": "Иванова",
    "middle_name": null,
    "birth_date": "2021-05-10",
    "status": "active",
    "group": {
      "id": "uuid",
      "name": "Ромашка",
      "status": "active"
    }
  }
}
```

---

# 26. Guardian detail

```json
{
  "id": "uuid",
  "first_name": "Анна",
  "last_name": "Иванова",
  "middle_name": null,
  "phone": "+79990000000",
  "email": "anna@example.test",
  "status": "active",
  "children": [],
  "account": null,
  "archived_at": null,
  "created_at": "2026-09-25T12:00:00Z",
  "updated_at": "2026-09-25T12:00:00Z"
}
```

`account`:
- null;
- либо ParentAccountSummary.

---

# 27. GET /guardians

Query:

```text
status=active|archived|all
q=string optional
```

Response:

```json
{
  "items": [
    {
      "id": "uuid",
      "first_name": "Анна",
      "last_name": "Иванова",
      "middle_name": null,
      "phone": null,
      "email": null,
      "status": "active",
      "account": null
    }
  ]
}
```

---

# 28. POST /guardians

Request:

```json
{
  "first_name": "Анна",
  "last_name": "Иванова",
  "middle_name": null,
  "phone": null,
  "email": null
}
```

Success:
- 201 Guardian detail.

phone/email optional.

---

# 29. GET /guardians/{guardian_id}

Success:
- 200 Guardian detail.

Errors:
- 404 NOT_FOUND.

---

# 30. PATCH /guardians/{guardian_id}

Request subset:

```json
{
  "first_name": "Анна",
  "last_name": "Иванова",
  "middle_name": null,
  "phone": null,
  "email": "anna@example.test"
}
```

Null clears optional field.

Success:
- 200 Guardian detail.

---

# 31. POST /guardians/{guardian_id}/archive

Precondition:
- no active relations to active children.

If linked PARENT account exists, archive operation atomically:
1. archives Guardian;
2. sets linked User status = `blocked`;
3. revokes active sessions.

Success:
- 200 Guardian detail.

Errors:

```text
404 NOT_FOUND
409 GUARDIAN_HAS_ACTIVE_CHILDREN
```

---

# 32. POST /guardians/{guardian_id}/restore

Restores Guardian only.

Security rule:
- linked PARENT account remains blocked after Guardian restore;
- DIRECTOR/ADMIN must explicitly call `/account/unblock`.

Success:
- 200 Guardian detail.

---

# 33. POST /children/{child_id}/guardians

Request:

```json
{
  "guardian_id": "uuid",
  "relation_type": "mother"
}
```

Preconditions:
- Child active;
- Guardian active;
- same current tenant.

Success:
- 201 for new relation;
- 200 if same archived pair is reactivated.

Response:
- ChildGuardian object.

Errors:

```text
404 NOT_FOUND
409 CHILD_ARCHIVED
409 GUARDIAN_ARCHIVED
409 RELATION_ALREADY_EXISTS
```

`RELATION_ALREADY_EXISTS` only when pair already active.

---

# 34. PATCH /children/{child_id}/guardians/{guardian_id}

Request:

```json
{
  "relation_type": "legal_guardian"
}
```

Success:
- 200 ChildGuardian object.

Archived/nonexistent relation:
- 404 `RELATION_NOT_FOUND` or `NOT_FOUND` according to implementation; public contract uses `RELATION_NOT_FOUND` only within current tenant.

Foreign tenant remains generic 404 `NOT_FOUND`.

---

# 35. POST /children/{child_id}/guardians/{guardian_id}/archive

Success:
- 200 ChildGuardian object archived.

No physical DELETE.

---

# 36. POST /children/{child_id}/guardians/{guardian_id}/restore

Preconditions:
- Child active;
- Guardian active.

Success:
- 200 ChildGuardian object active.

Errors:

```text
404 NOT_FOUND
409 CHILD_ARCHIVED
409 GUARDIAN_ARCHIVED
```

---

# 37. POST /guardians/{guardian_id}/account

Preconditions:
- Guardian active;
- Guardian current tenant;
- no existing account.

Request body отсутствует.

Success 201:

```json
{
  "account": {
    "id": "uuid",
    "username": "parent-k4m8r2q9",
    "status": "active",
    "must_change_password": true
  },
  "temporary_password": "random-value-shown-once"
}
```

Security:
- temporary_password only this response;
- no GET endpoint can return it;
- no logging.

Errors:

```text
404 NOT_FOUND
409 GUARDIAN_ARCHIVED
409 PARENT_ACCOUNT_ALREADY_EXISTS
```

---

# 38. POST /guardians/{guardian_id}/account/reset-password

Request body отсутствует.

Success 200:

```json
{
  "account": {
    "id": "uuid",
    "username": "parent-k4m8r2q9",
    "status": "active",
    "must_change_password": true
  },
  "temporary_password": "new-random-value-shown-once"
}
```

Effect:
- old password invalid;
- all old sessions revoked;
- must_change_password=true.

Errors:
- 404 PARENT_ACCOUNT_NOT_FOUND / NOT_FOUND.

Reset may be performed for active or blocked PARENT; reset does not automatically unblock a blocked account.

---

# 39. POST /guardians/{guardian_id}/account/block

Success:
- 200 ParentAccountSummary with `status=blocked`.

Effect:
- revoke all active sessions.

Operation is idempotent.

---

# 40. POST /guardians/{guardian_id}/account/unblock

Precondition:
- Guardian active.

Success:
- 200 ParentAccountSummary with `status=active`.

Does not issue a session.

Errors:

```text
404 NOT_FOUND
409 GUARDIAN_ARCHIVED
```

Operation is idempotent.

---

# 41. Validation rules

## Names

After trim:
- required names 1–100 chars;
- optional middle_name empty string → null.

## Group name

After trim:
- 1–100 chars.

## Birth date

- date-only YYYY-MM-DD;
- cannot be future.

## Email

- optional;
- valid email syntax;
- normalized lower-case;
- empty → null.

## Phone

- optional;
- max 32 chars;
- trim;
- empty → null.

Stage 2 не использует phone as credential.

---

# 42. No client organization_id

Create/update bodies Stage 2 must not accept:

```json
{
  "organization_id": "..."
}
```

Tenant always comes from authenticated session.

Если extra fields запрещены schema policy, такой input → 400 VALIDATION_ERROR.

---

# 43. Error code registry Stage 2

```text
NOT_FOUND

GROUP_NAME_CONFLICT
GROUP_NOT_EMPTY
GROUP_ARCHIVED

INVALID_BIRTH_DATE
CHILD_ARCHIVED

GUARDIAN_ARCHIVED
GUARDIAN_HAS_ACTIVE_CHILDREN

RELATION_ALREADY_EXISTS
RELATION_NOT_FOUND

PARENT_ACCOUNT_ALREADY_EXISTS
PARENT_ACCOUNT_NOT_FOUND
PARENT_ACCOUNT_BLOCKED

INVALID_CREDENTIALS
USER_BLOCKED
ORGANIZATION_BLOCKED
PASSWORD_CHANGE_REQUIRED
INVALID_PASSWORD
UNAUTHORIZED
FORBIDDEN
VALIDATION_ERROR
INTERNAL_ERROR
```

---

# 44. Transport naming

Все JSON fields:

```text
snake_case
```

Не вводить Frontend-specific aliases в HTTP contract.

---

# 45. Date/time

Datetime:
- UTC ISO8601, suffix Z when serialized.

Date-only:
- YYYY-MM-DD;
- no timezone conversion.

---

# 46. Security invariants

Во всех endpoints:
- no raw session token in JSON;
- no password_hash;
- no temporary password except account create/reset response;
- no foreign tenant existence leak;
- PARENT denied management API;
- blocked User denied auth/current session;
- archived Guardian cannot have an unblocked active Parent account after archive action;
- Frontend visibility is not authorization.

---

# 47. Contract acceptance scenarios

Contract считается реализованным только если automated/browser tests подтверждают:

1. DIRECTOR creates Group.
2. Creates Child in Group.
3. Creates Guardian without phone/email.
4. Links Guardian ↔ Child.
5. Creates PARENT account.
6. PARENT logs in with temporary password.
7. PARENT changes password.
8. PARENT reaches only technical parent screen.
9. PARENT cannot GET /children.
10. One Guardian can link to two Child.
11. One Child can link to two Guardian.
12. Tenant A cannot access/relate Tenant B entities.
13. Group with active Child cannot archive.
14. Guardian with active Child relation cannot archive.
15. Guardian archive blocks its Parent User and revokes sessions.
16. Parent reset invalidates old password/sessions.
17. No temporary password can be retrieved after create/reset response.
