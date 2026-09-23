# API Contract v0.1 — Этап 1

Этот документ обязателен для обоих разработчиков.

Изменение контракта производится только согласованно.

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

# 3. POST /auth/login

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

# 4. GET /auth/me

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

# 5. POST /auth/change-password

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

Errors:

```text
400 INVALID_PASSWORD
401 UNAUTHORIZED
```

После успеха ранее выданные сессии должны обрабатываться по утверждённой политике инвалидирования.

---

# 6. POST /auth/logout

Request body отсутствует.

Success:

```json
{
  "success": true
}
```

---

# 7. HTTP status policy

```text
200 — success
201 — created
400 — bad request / validation
401 — unauthenticated
403 — authenticated, but forbidden/blocked
404 — entity not found or hidden by tenant isolation policy
409 — conflict
422 — optional validation policy if team chooses FastAPI default
500 — unexpected server error
```

Команда должна выбрать одну политику для validation (`400` или `422`) и придерживаться её.

---

# 8. Naming

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

# 9. Date/time

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

# 10. Security contract

- password не возвращается;
- password_hash не возвращается;
- auth credentials не передаются в URL;
- client-supplied `organization_id` не определяет tenant context;
- Frontend скрывает недоступные действия, Backend их реально запрещает.
