# API Contract Stage 3 — Employees / Attendance

**Base:** `/api/v1`. JSON `snake_case`, UUID strings, dates `YYYY-MM-DD`, times `HH:MM` local wall time. Сессия `smart_garden_session` HttpOnly; tenant только из authenticated User. Stage 1/2 API не меняется. Все ошибки:

```json
{"error":{"code":"NOT_FOUND","message":"Запись не найдена.","field":null}}
```

Текст ошибки фиксированный и безопасный, `field` — имя поля или null. Validation → HTTP 400 `VALIDATION_ERROR`; no session → 401 `UNAUTHORIZED`; недостаточно роли → 403 `FORBIDDEN`; чужой UUID → 404 `NOT_FOUND`. Каждый endpoint документирует error responses в OpenAPI.

## 1. Employee transport

```json
{
  "id":"uuid", "first_name":"Анна", "last_name":"Тестовая", "middle_name":null,
  "position":"Администратор", "status":"active",
  "account":{"id":"uuid","username":"staff-k4m8r2q9","role":"ADMIN","status":"active","must_change_password":true},
  "archived_at":null, "created_at":"2026-09-26T09:00:00Z", "updated_at":"2026-09-26T09:00:00Z"
}
```

`account` nullable. List item содержит id, ФИО, position, status и account summary без timestamps. Detail содержит все поля примера. Ни в каком GET нет password/hash/session token или organization_id. Request create:

```json
{"first_name":"Анна","last_name":"Тестовая","middle_name":null,"position":"Администратор"}
```

PATCH принимает непустое подмножество этих полей; required first_name/last_name/position нельзя обнулить. Пробелы trim, 1–100 после trim, пустое middle_name → null. Любое extra field, в том числе `organization_id`, `user_id`, `role` → 400.

## 2. Employee routes

| Method | Route | Role | Success | Особое правило |
|---|---|---|---|---|
| GET | `/employees?status=active\|archived\|all&q=...` | DIRECTOR, ADMIN | 200 `{ "items": [...] }` | Default active; q optional max 100, без query с ФИО из Frontend |
| POST | `/employees` | DIRECTOR, ADMIN | 201 detail | Account не создаётся |
| GET | `/employees/{id}` | DIRECTOR, ADMIN | 200 detail | Чужой id → 404 |
| PATCH | `/employees/{id}` | DIRECTOR, ADMIN | 200 detail | Account и роль не меняются |
| POST | `/employees/{id}/archive` | DIRECTOR; ADMIN лишь без User | 200 detail | Со связанным User блокировка и отзыв сессий атомарны |
| POST | `/employees/{id}/restore` | DIRECTOR, ADMIN | 200 detail | User остаётся blocked |

Archive/restore идемпотентны. Тело archive/restore отсутствует. Возможные бизнес-ошибки: `404 NOT_FOUND`, `403 FORBIDDEN`; validation `400 VALIDATION_ERROR`.

## 3. Employee ADMIN account

Все маршруты только DIRECTOR, тело запроса отсутствует:

| Method | Route | Success |
|---|---|---|
| POST | `/employees/{id}/account` | 201 `{ "account": EmployeeAccountSummary, "temporary_password": "random" }` |
| POST | `/employees/{id}/account/reset-password` | 200 тот же one-time response |
| POST | `/employees/{id}/account/block` | 200 `EmployeeAccountSummary` |
| POST | `/employees/{id}/account/unblock` | 200 `EmployeeAccountSummary` |

`EmployeeAccountSummary`: `id`, `username`, `role="ADMIN"`, `status=active|blocked`, `must_change_password`. Пароль есть **только** в create/reset response, не в GET Employee. Create требует активного Employee без account, иначе `409 EMPLOYEE_ARCHIVED` / `409 EMPLOYEE_ACCOUNT_ALREADY_EXISTS`; reset/block/unblock без account → `404 EMPLOYEE_ACCOUNT_NOT_FOUND`. Reset отзываeт все сессии и не разблокирует User. Block идемпотентен и отзывает сессии. Unblock идемпотентен, допускается лишь при активном Employee (`409 EMPLOYEE_ARCHIVED`), не выдаёт сессию. Архивный Employee нельзя снабдить новым доступом.

## 4. Attendance day row

```json
{
  "record_id":null, "date":"2026-09-26",
  "child":{"id":"uuid","first_name":"София","last_name":"Тестовая","middle_name":null,"status":"active"},
  "group":{"id":"uuid","name":"Ромашка"},
  "status":"unknown", "arrival_time":null, "departure_time":null
}
```

`record_id=null` означает вычисленную строку без сохранённой отметки. В сохранённой строке record_id UUID; group — снимок при первой отметке. `GET /attendance/{record_id}` возвращает эту строку плюс `created_at`, `updated_at`, `created_by`, `updated_by` UUID. Не возвращать ФИО автора или скрытые поля Child/Guardian.

## 5. Attendance routes

| Method | Route | Role | Success |
|---|---|---|---|
| GET | `/attendance?date=YYYY-MM-DD&group_id=uuid&status=all\|present\|absent\|unknown&child_id=uuid` | DIRECTOR, ADMIN | 200 `{ "items": [day row] }` |
| POST | `/attendance` | DIRECTOR, ADMIN | 201 created detail или 200 updated detail |
| GET | `/attendance/{record_id}` | DIRECTOR, ADMIN | 200 saved detail |
| PATCH | `/attendance/{record_id}` | DIRECTOR, ADMIN | 200 updated detail |

GET требует date, optional filters; default status all. Фильтр чужого group_id/child_id → 404. Для активного Child без записи — computed unknown; архивный Child включается только если у него уже есть запись на эту дату. Чужие записи не видны. Сортировка group/name/id, без pagination Stage 3.

POST body:

```json
{"child_id":"uuid","date":"2026-09-26","status":"present","arrival_time":"08:30","departure_time":null}
```

Повтор POST для той же пары child/date обновляет строку, не создаёт вторую. `created_by` сохраняется, `updated_by` меняется. `group_id` фиксируется при первой записи. PATCH принимает непустое подмножество `status`, `arrival_time`, `departure_time`; immutable child/date/group/actor/tenant запрещены. Для absent/unknown времена обязаны быть null; при смене статуса на них сервис очищает прежние времена. Для present оба времени optional, но departure без arrival или раньше arrival → 400 `INVALID_ATTENDANCE_TIME`. Дата в будущем → 400 `INVALID_ATTENDANCE_DATE`; чужой Child/Group → 404; archived Child → 409 `CHILD_ARCHIVED`; archived Group при новой отметке → 409 `GROUP_ARCHIVED`. Нет comment/reason/medical fields и DELETE.

## 6. Security и acceptance

PARENT получает 403 на все новые management endpoints. ADMIN получает 403 на account endpoints и на archive Employee со связанным User. Tenant A не может читать Employee/Attendance или использовать Child/Group tenant B. Заблокированный ADMIN теряет действующие сессии. Временный пароль только в create/reset response. Dev/test/seed только синтетические данные; реальные ПДн до отдельной проверки по 152-ФЗ не загружать.

Browser E2E: DIRECTOR создаёт Employee и account, ADMIN меняет пароль; ADMIN не может управлять аккаунтами; директор блокирует, сбрасывает, архивирует; посещаемость unknown → present → absent на одном ребёнке/дате, фильтры и история группы; PARENT denied; Stage 1/2 regression green.
