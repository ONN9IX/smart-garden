# ТЗ Stage 2 — Backend

**Проект:** Умный сад  
**Этап:** Stage 2 — Groups / Children / Guardians / PARENT account  
**Исполнитель Stage 2:** ONN9IX  
**Статус:** Ready for development после merge этого документа и API Contract  
**Источник решений:** `docs/12-stage-2-data-model-and-decisions.md`  
**Обязательно прочитать:** `docs/00-development-guide.md`, `docs/03-api-contract-v0.1.md`, `docs/05-personal-data-baseline.md`, `docs/08-team-access-and-environments.md`, `docs/09-code-and-error-standards.md`.

---

# 0. Цель Backend Stage 2

Реализовать серверную часть первого бизнес-сценария:

```text
DIRECTOR / ADMIN
→ Group
→ Child
→ Guardian
→ ChildGuardian
→ PARENT account
```

К концу этапа Frontend не должен содержать mock-данные для этих сущностей.

---

# 1. Что уже есть и не переписывается

Сохраняются:

- FastAPI;
- PostgreSQL;
- SQLAlchemy 2.x;
- Alembic;
- Argon2id;
- server-side sessions;
- HttpOnly cookie `smart_garden_session`;
- общий error contract;
- tenant context через authenticated User;
- `require_role(...)`;
- `require_tenant(...)`;
- CI;
- synthetic seed.

Не вводить:
- JWT;
- вторую БД;
- Firebase/Supabase;
- localStorage auth;
- отдельный Backend для Parent.

---

# 2. Обязательные изменения существующего auth

Сейчас `backend/app/services/auth.py` разрешает только роли DIRECTOR/ADMIN.

Stage 2 должен разрешить `PARENT` для базового auth lifecycle:

```text
login
/auth/me
/change-password
/logout
```

Но PARENT не получает доступ к management API.

Правило:

```python
current_identity → DIRECTOR | ADMIN | PARENT
current_user → DIRECTOR | ADMIN | PARENT, но must_change_password=False
management endpoints → require_role("DIRECTOR", "ADMIN")
```

Не использовать проверку роли только во Frontend.

---

# 3. Миграции

Создать последовательные Alembic migrations после текущей `0003`.

Рекомендуемая последовательность:

```text
0004_expand_user_role_parent.py
0005_groups_children.py
0006_guardians_child_guardians.py
```

## 3.1. 0004

Изменить DB constraint ролей User:

было:

```text
DIRECTOR
ADMIN
```

станет:

```text
DIRECTOR
ADMIN
PARENT
```

Новый check constraint должен иметь явное имя.

Одновременно обновить SQLAlchemy model `User.__table_args__`.

Downgrade обязан вернуть Stage 1 constraint.

## 3.2. 0005

Создать:
- `groups`;
- `children`.

Все поля и ограничения — строго по `docs/12-stage-2-data-model-and-decisions.md`.

## 3.3. 0006

Создать:
- `guardians`;
- `child_guardians`.

Guardian.user_id:
- nullable;
- FK `users.id`;
- unique when not null.

ChildGuardian:
- unique pair `(child_id, guardian_id)`.

---

# 4. Models

Создать:

```text
backend/app/models/group.py
backend/app/models/child.py
backend/app/models/guardian.py
backend/app/models/child_guardian.py
```

Обновить:

```text
backend/app/models/__init__.py
backend/app/db/base.py
backend/app/models/user.py
```

Каждый файл — с module docstring по стандарту проекта.

---

# 5. Group model

Поля:

```text
id UUID PK
organization_id UUID FK organizations.id
name varchar(100)
status active|archived
archived_at timestamptz nullable
created_at timestamptz
updated_at timestamptz
```

Backend обязан:
- trim name;
- не принимать organization_id из request;
- не разрешать duplicate active group name в одном tenant;
- допускать одинаковые names в разных tenant;
- не архивировать group с active children.

Ошибка:

```text
409 GROUP_NOT_EMPTY
```

---

# 6. Child model

Поля:

```text
id UUID PK
organization_id UUID FK
group_id UUID FK
first_name varchar(100)
last_name varchar(100)
middle_name nullable varchar(100)
birth_date date
status active|archived
archived_at timestamptz nullable
created_at
updated_at
```

Правила:
- first_name/last_name required;
- middle_name empty → null;
- birth_date не в будущем;
- active Child всегда имеет active Group своей organization;
- group transfer внутри tenant разрешён;
- duplicate ФИО+birth_date допустим;
- никаких medical/document/photo fields.

---

# 7. Guardian model

Поля:

```text
id UUID PK
organization_id UUID FK
user_id UUID FK users.id nullable unique
first_name varchar(100)
last_name varchar(100)
middle_name nullable
phone nullable varchar(32)
email nullable varchar(254)
status active|archived
archived_at nullable
created_at
updated_at
```

Правила:
- phone/email optional;
- email normalize lower-case;
- username из phone/email не строить;
- Guardian не архивировать при active ChildGuardian links к active children;
- если Guardian архивируется и у него есть PARENT account, в той же transaction User блокируется и его active sessions revoked;
- restore Guardian не разблокирует PARENT account автоматически;
- никаких скрытых cascade delete бизнес-связей.

Ошибка:

```text
409 GUARDIAN_HAS_ACTIVE_CHILDREN
```

---

# 8. ChildGuardian model

Поля:

```text
id UUID PK
organization_id UUID FK
child_id UUID FK
guardian_id UUID FK
relation_type mother|father|legal_guardian|other
status active|archived
archived_at nullable
created_at
updated_at
```

Правила:
- child + guardian только одного tenant;
- pair уникальна;
- повторное добавление archived pair → restore existing row;
- relation_type можно изменить;
- unlink = archive relation, не DELETE.

---

# 9. Schemas

Создать:

```text
backend/app/schemas/group.py
backend/app/schemas/child.py
backend/app/schemas/guardian.py
backend/app/schemas/parent_account.py
```

Pydantic schemas должны:
- не содержать organization_id в create/update request;
- не содержать password_hash;
- не содержать raw session token;
- нормализовать empty optional strings;
- отдавать только документированные поля.

---

# 10. Services

Бизнес-логику не складывать в route handlers.

Создать:

```text
backend/app/services/groups.py
backend/app/services/children.py
backend/app/services/guardians.py
backend/app/services/parent_accounts.py
```

Services отвечают за:
- tenant-scoped queries;
- business validation;
- archive/restore;
- transactions;
- account lifecycle.

Route handlers должны быть тонкими.

---

# 11. API routers

Создать:

```text
backend/app/api/groups.py
backend/app/api/children.py
backend/app/api/guardians.py
```

Подключить в `backend/app/main.py` с prefix:

```text
/api/v1
```

Все management routes:

```text
require_role("DIRECTOR", "ADMIN")
```

---

# 12. CORS / methods

Текущий API client Stage 1 использует GET/POST.

Stage 2 добавляет PATCH.

В Backend:
- добавить `PATCH` в CORS allow_methods;
- origin middleware уже обязан продолжать fail closed для PATCH;
- DELETE не нужен.

---

# 13. Group endpoints

Реализовать:

```text
GET   /groups
POST  /groups
GET   /groups/{group_id}
PATCH /groups/{group_id}
POST  /groups/{group_id}/archive
POST  /groups/{group_id}/restore
```

GET /groups query:
- `status=active|archived|all`;
- default `active`.

Не добавлять pagination на Stage 2.

Response list:

```json
{
  "items": []
}
```

---

# 14. Child endpoints

Реализовать:

```text
GET   /children
POST  /children
GET   /children/{child_id}
PATCH /children/{child_id}
POST  /children/{child_id}/archive
POST  /children/{child_id}/restore
```

GET /children query:
- `status=active|archived|all`;
- `group_id` optional;
- `q` optional search by ФИО;
- default status active.

Child detail response включает:
- basic Child;
- Group summary;
- active Guardian links.

---

# 15. Guardian endpoints

Реализовать:

```text
GET   /guardians
POST  /guardians
GET   /guardians/{guardian_id}
PATCH /guardians/{guardian_id}
POST  /guardians/{guardian_id}/archive
POST  /guardians/{guardian_id}/restore
```

GET /guardians query:
- status;
- q by ФИО;
- default active.

Guardian detail включает:
- basic Guardian;
- linked children;
- account summary или null.

---

# 16. Child ↔ Guardian endpoints

Реализовать:

```text
POST  /children/{child_id}/guardians
PATCH /children/{child_id}/guardians/{guardian_id}
POST  /children/{child_id}/guardians/{guardian_id}/archive
POST  /children/{child_id}/guardians/{guardian_id}/restore
```

Create body:

```json
{
  "guardian_id": "uuid",
  "relation_type": "mother"
}
```

PATCH body:

```json
{
  "relation_type": "legal_guardian"
}
```

---

# 17. PARENT account endpoints

Реализовать через Guardian resource:

```text
POST /guardians/{guardian_id}/account
POST /guardians/{guardian_id}/account/reset-password
POST /guardians/{guardian_id}/account/block
POST /guardians/{guardian_id}/account/unblock
```

Не делать отдельный общий users-admin endpoint Stage 2.

## 17.1. Create account

Допускается только если:
- Guardian active;
- tenant current;
- guardian.user_id is null.

Генерация username:
- prefix `parent-`;
- random lowercase alphanumeric suffix;
- без ФИО/телефона/email;
- retry при collision.

Temporary password:
- использовать существующий `generate_temporary_password()`;
- хранить только Argon2id hash;
- plaintext вернуть только один раз.

Response:

```json
{
  "account": {
    "id": "uuid",
    "username": "parent-k4m8r2q9",
    "status": "active",
    "must_change_password": true
  },
  "temporary_password": "shown-once"
}
```

## 17.2. Reset password

В одной transaction:
1. generate temp password;
2. replace password_hash;
3. must_change_password=true;
4. revoke all AuthSession for user;
5. commit;
6. return plaintext once.

## 17.3. Block

- user.status = blocked;
- revoke active sessions;
- commit.

## 17.4. Unblock

- user.status = active;
- не создавать новую session;
- пользователь входит обычным способом.

---

# 18. PARENT auth

Обновить:

```text
backend/app/services/auth.py
backend/app/models/user.py
backend/alembic...
```

`authenticate_credentials` и `current_identity` должны принимать PARENT.

Но business routes не используют просто `current_user` без role guard.

Для management API:

```python
Depends(require_role("DIRECTOR", "ADMIN"))
```

PARENT management request → 403 FORBIDDEN.

Для PARENT auth также fail closed: связанный Guardian должен существовать в том же tenant и быть active. Архивация Guardian всё равно обязана блокировать User и revoke sessions.

---

# 19. Error codes

Поддержать минимум:

```text
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
VALIDATION_ERROR
FORBIDDEN
UNAUTHORIZED
```

Не возвращать DB/SQL details.

Чужой tenant entity → 404 `NOT_FOUND`. Для этого Stage 2 допускает обновление существующего tenant guard, чтобы он не возвращал публичный код `FORBIDDEN` при HTTP 404.

---

# 20. Transactions

Обязательная transaction atomicity:
- parent account create;
- parent password reset + revoke sessions;
- block + revoke sessions;
- ChildGuardian reactivation;
- archive/restore operations, если затрагивается больше одного поля.

Никакого `except Exception: pass`.

---

# 21. Tests

Создать test modules минимум:

```text
backend/tests/test_groups.py
backend/tests/test_children.py
backend/tests/test_guardians.py
backend/tests/test_parent_accounts.py
backend/tests/test_stage2_tenant_isolation.py
backend/tests/test_stage2_rbac.py
```

## 21.1. Group tests

Проверить:
- create;
- duplicate active name conflict;
- same name other tenant allowed;
- update;
- archive empty;
- archive non-empty → 409;
- restore.

## 21.2. Child tests

Проверить:
- create;
- future birth_date rejected;
- group foreign tenant hidden;
- transfer same tenant;
- archive/restore;
- archived group cannot receive child.

## 21.3. Guardian tests

Проверить:
- create with no phone/email;
- update;
- archive no links;
- archive active link blocked.

## 21.4. Relation tests

Проверить:
- one guardian → several children;
- one child → several guardians;
- duplicate relation handling;
- archive/restore link;
- cross-tenant link impossible.

## 21.5. Parent account tests

Проверить:
- create;
- duplicate create blocked;
- temp password works;
- must_change_password flow;
- reset invalidates old password;
- reset revokes sessions;
- block revokes sessions;
- PARENT can auth;
- PARENT cannot management endpoints.

---

# 22. Tenant test fixture

Tests должны иметь минимум:

```text
Organization A
Organization B
Director A
Admin A
Parent A
Director B
Group A / Group B
Child A / Child B
Guardian A / Guardian B
```

Никаких реальных данных.

---

# 23. Seed

Обновить `backend/app/services/seed.py` только synthetic данными.

После Stage 2 seed должен уметь создать пример:
- Group «Ромашка»;
- synthetic Child;
- synthetic Guardian;
- ChildGuardian relation.

PARENT account в seed:
- допускается synthetic;
- temporary password показывается локально один раз;
- не commit в Git.

Seed повторный запуск должен быть idempotent.

---

# 24. OpenAPI

Проверить:
- все новые endpoints присутствуют;
- schemas читаемые;
- error responses документированы;
- temporary_password есть только в create/reset responses;
- organization_id отсутствует в unsafe request schemas.

---

# 25. Комментарии

Каждый новый нетривиальный source file обязан иметь module docstring:
- назначение;
- вход/выход;
- tenant/security restriction.

Не писать комментарии вида:

```python
# create group
```

если это и так очевидно.

---

# 26. Логи и ПДн

Никогда не логировать:
- ФИО целиком без технической необходимости;
- phone/email payload;
- birth_date;
- password/temp password;
- password hash;
- session token;
- request body business forms.

Допустимо логировать:
- event type;
- entity UUID;
- organization UUID;
- actor user UUID;
- result/status;
если это нужно технически.

Audit Log как бизнес-модуль остаётся Stage 4.

---

# 27. Проверки разработчика перед PR

В `backend/`:

```bash
ruff check .
pytest
```

В корне:
- Alembic upgrade head;
- downgrade base;
- upgrade head повторно;
- preview compose;
- Browser E2E не должен сломаться.

---

# 28. Definition of Done Backend Stage 2

Backend часть готова только если:

- [ ] PARENT добавлен в User role constraint;
- [ ] migrations upgrade/downgrade работают;
- [ ] Group CRUD/archive/restore готов;
- [ ] Child CRUD/archive/restore готов;
- [ ] Guardian CRUD/archive/restore готов;
- [ ] ChildGuardian many-to-many готов;
- [ ] PARENT account create/reset/block/unblock готов;
- [ ] PARENT auth работает;
- [ ] archived Guardian не может сохранять активный PARENT access;
- [ ] PARENT management API запрещён;
- [ ] tenant tests для двух организаций зелёные;
- [ ] cross-tenant link невозможен;
- [ ] plaintext temp password нигде не сохраняется;
- [ ] ruff green;
- [ ] pytest green;
- [ ] OpenAPI соответствует Stage 2 API Contract;
- [ ] Frontend может пройти весь happy path без mock.
