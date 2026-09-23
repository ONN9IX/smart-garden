# API Contract v0.1 — Этап 1

**Кому читать:** обоим разработчикам перед любой задачей, затрагивающей HTTP/API.  
**Статус:** источник истины по сетевому контракту Stage 1.  
**Изменения:** только согласованно, с синхронным обновлением Backend, Frontend, Issues и master draft.

Этот документ обязателен для обоих разработчиков.

Base path:

```text
/api/v1
```

---

# 1. Общие роли

```text
DIRECTOR
ADMIN
```

Зарезервированы на будущее:

```text
PARENT
TEACHER
SUPER_ADMIN
```

---

# 2. Общий формат ошибки

```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Неверный логин или пароль",
    "field": null
  }
}
```

---

# 3. Сессия Stage 1

Используется server-side session.

- Backend генерирует криптографически случайный session token.
- В браузер token попадает только через cookie `smart_garden_session`.
- Cookie: `HttpOnly`; production: `Secure`; `SameSite=Lax`.
- Frontend не получает token в JSON и не читает его JavaScript-кодом.
- В PostgreSQL хранится только hash session token, а не raw token.
- Logout отзывает текущую session и очищает cookie.
- Смена временного пароля отзывает старые sessions и выдаёт новую session.
- Истёкшая/revoked session → 401 `UNAUTHORIZED`.

Минимальная серверная модель `AuthSession`:
```text
id UUID
user_id UUID
token_hash
created_at
expires_at
revoked_at optional
last_seen_at optional
```

# 4. POST /auth/login

Request:

```json
{
  "username": "director-demo",
  "password": "example-password"
}
```

Success:

```json
{
  "user": {
    "id": "uuid",
    "username": "director-demo",
    "role": "DIRECTOR",
    "status": "active",
    "must_change_password": false
  },
  "organization": {
    "id": "uuid",
    "name": "Детский сад «Солнышко»"
  }
}
```

В случае временного пароля:

```json
{
  "user": {
    "id": "uuid",
    "username": "admin-demo",
    "role": "ADMIN",
    "status": "active",
    "must_change_password": true
  },
  "organization": {
    "id": "uuid",
    "name": "Детский сад «Солнышко»"
  }
}
```

Errors:

```text
401 INVALID_CREDENTIALS
403 USER_BLOCKED
403 ORGANIZATION_BLOCKED
```

---

# 5. GET /auth/me

Success:

```json
{
  "user": {
    "id": "uuid",
    "username": "director-demo",
    "role": "DIRECTOR",
    "status": "active",
    "must_change_password": false
  },
  "organization": {
    "id": "uuid",
    "name": "Детский сад «Солнышко»"
  }
}
```

Errors:

```text
401 UNAUTHORIZED
403 USER_BLOCKED
403 ORGANIZATION_BLOCKED
```

---

# 6. POST /auth/change-password

Request:

```json
{
  "new_password": "new-secure-password"
}
```

Success:

```json
{
  "success": true,
  "must_change_password": false
}
```

Stage 1 endpoint используется **только для обязательной смены временного пароля**, когда `must_change_password=true`.

Errors:

```text
400 INVALID_PASSWORD
401 UNAUTHORIZED
403 FORBIDDEN
```

Если `must_change_password=false`, endpoint не используется как обычная смена постоянного пароля и возвращает 403. Обычная смена пароля с подтверждением текущего пароля проектируется отдельно позже.

После успеха:
- новый password hash сохранён;
- `must_change_password=false`;
- старые sessions revoked;
- текущая временная session заменена новой session;
- старый временный пароль не работает.

---

# 7. POST /auth/logout

Request body отсутствует.

Success:

```json
{
  "success": true
}
```

Backend отзывает текущую server-side session и очищает cookie `smart_garden_session`.

---

# 8. HTTP status policy

```text
200 — success
201 — created
400 — bad request / validation
401 — unauthenticated
403 — authenticated, but forbidden/blocked
404 — entity not found or hidden by tenant isolation policy
409 — conflict
500 — unexpected server error
```

**Validation policy зафиксирована: HTTP 400.** FastAPI/Pydantic validation errors, видимые клиенту, нормализуются в общий error contract с кодом `VALIDATION_ERROR`. Frontend не должен отдельно обрабатывать FastAPI 422.

---

# 9. Naming

API JSON:

```text
snake_case
```

Пример:

```text
must_change_password
organization_id
first_name
```

Frontend не переименовывает поля в transport layer без необходимости.

---

# 10. Date/time

Datetime:

```text
ISO 8601 UTC
```

Пример:

```text
2026-09-23T12:30:00Z
```

Frontend отображает в локальном часовом поясе пользователя/сада по дальнейшим требованиям.

---

# 11. Security contract

- все Stage 1 entity IDs в API — UUID strings;
- password не возвращается;
- password_hash не возвращается;
- raw session token не возвращается JSON/API body;
- auth credentials не передаются в URL;
- client-supplied `organization_id` не определяет tenant context;
- Frontend скрывает недоступные действия, Backend их реально запрещает.
