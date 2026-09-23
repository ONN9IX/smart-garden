# ТЗ Этап 1 — Backend / Core

**Проект:** Умный сад  
**Версия:** MVP 0.1  
**Исполнитель:** Backend-разработчик  
**Статус:** Ready for development

---

## 1. Цель этапа

Создать безопасный серверный фундамент SaaS-системы, на котором дальше будут строиться дети, группы, родители, сотрудники и посещаемость.

После завершения Этапа 1 Backend должен уметь:

1. хранить несколько независимых детских садов;
2. хранить пользователей конкретного сада;
3. различать роли `DIRECTOR` и `ADMIN`;
4. авторизовывать пользователя по `username + password`;
5. поддерживать временный пароль;
6. требовать обязательную смену временного пароля;
7. блокировать пользователя;
8. запрещать доступ к данным другой организации;
9. отдавать текущего пользователя через API;
10. иметь миграции, базовые тесты и API-документацию.

На этом этапе **не реализовывать** детей, родителей, группы, посещаемость и объявления.

---

# 2. Рекомендуемый стек

- Python 3.12+
- FastAPI
- PostgreSQL
- SQLAlchemy 2.x
- Alembic
- Pydantic
- pytest

Допускается изменение стека только до начала реализации при совместном решении команды.

---

# 3. Структура проекта

Рекомендуемый ориентир:

```text
backend/
├── app/
│   ├── api/
│   │   ├── auth.py
│   │   └── health.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── permissions.py
│   ├── db/
│   │   ├── base.py
│   │   └── session.py
│   ├── models/
│   │   ├── organization.py
│   │   └── user.py
│   ├── schemas/
│   │   ├── auth.py
│   │   └── user.py
│   ├── services/
│   │   └── auth.py
│   └── main.py
├── alembic/
├── tests/
├── .env.example
├── requirements.txt / pyproject.toml
└── README.md
```

Это ориентир, а не обязательная архитектурная догма.

---

# 4. Environment

Локальная Backend-среда должна быть воспроизводима любым разработчиком без запроса чужих паролей.

Основной способ запуска PostgreSQL в dev:

```bash
docker compose up -d postgres
```

Корневой `docker-compose.yml` поднимает локальную PostgreSQL:
- database: `smart_garden`;
- user: `smart_garden`;
- dev-only password: `smart_garden_local_only`;
- port: `127.0.0.1:5432`.

Этот пароль относится только к локальному synthetic environment и запрещён для staging/production.

Создать `backend/.env.example`:

```env
APP_ENV=development
DATABASE_URL=postgresql+psycopg://smart_garden:smart_garden_local_only@localhost:5432/smart_garden
SECRET_KEY=CHANGE_ME_LOCAL
AUTH_TOKEN_TTL=3600
CORS_ORIGINS=http://localhost:3000
```

Каждый разработчик копирует его в локальный `.env` и создаёт собственный local `SECRET_KEY`. Спрашивать локальный SECRET_KEY у предыдущего Backend-разработчика не нужно.

Production/shared secrets запрещено коммитить.

`.env` должен находиться в `.gitignore`.

Полная политика смены ролей и доступов: `docs/08-team-access-and-environments.md`.

---

# 5. Healthcheck

Реализовать:

```http
GET /api/v1/health
```

Ответ:

```json
{
  "status": "ok"
}
```

Endpoint не требует авторизации.

---

# 6. Сущность Organization

Организация = один детский сад / один клиент SaaS.

Минимальная модель:

```text
id
name
status
created_at
updated_at
```

`status`:

- `active`
- `blocked`
- `archived`

На Этапе 1 контактные данные сада можно не реализовывать.

## Требования

- `id` — UUID либо другой согласованный безопасный идентификатор;
- каждая пользовательская сущность в будущем должна иметь принадлежность к `organization_id`;
- заблокированная организация не должна получать рабочий доступ к API.

---

# 7. Сущность User

Минимальная модель:

```text
id
organization_id
username
password_hash
role
status
must_change_password
created_at
updated_at
last_login_at
```

Роли Этапа 1:

```text
DIRECTOR
ADMIN
```

Статусы:

```text
active
blocked
archived
```

## Username

Требования:

- обязателен;
- уникален глобально в системе;
- хранить в нормализованном виде;
- сравнение должно быть нечувствительно к регистру;
- запрещать пробелы по краям;
- определить допустимые символы до реализации.

Рекомендуемый формат:

```text
director-demo
admin-demo
```

Email не используется для авторизации и не является обязательным полем.

---

# 8. Пароли

## Обязательные правила

Нельзя хранить:

```text
password
temporary_password
```

в БД в открытом виде.

Хранится только:

```text
password_hash
```

Использовать современное адаптивное хеширование паролей, например Argon2id или bcrypt с корректной конфигурацией.

Пароли запрещено писать:

- в application logs;
- в Audit Log;
- в exception messages;
- в analytics.

---

# 9. Временный пароль

При создании пользователя система должна уметь сгенерировать криптографически случайный временный пароль.

После создания:

```text
must_change_password = true
```

Временный пароль возвращается вызывающей стороне только в момент создания/сброса.

Получить старый временный пароль повторно невозможно.

---

# 10. Первый вход

Сценарий:

```text
Пользователь
→ вводит username/password
→ Backend проверяет данные
→ если must_change_password = true
→ пользователь считается аутентифицированным только для операции смены пароля
→ основной API до смены пароля недоступен
→ пользователь устанавливает новый пароль
→ must_change_password = false
→ старый временный пароль больше не работает
```

Frontend должен иметь возможность определить этот статус через ответ login или `/auth/me`.

---

# 11. Авторизация

Реализовать:

```http
POST /api/v1/auth/login
POST /api/v1/auth/change-password
POST /api/v1/auth/logout
GET  /api/v1/auth/me
```

Точный JSON зафиксирован в `03-api-contract-v0.1.md`.

## Сессия / токен

Допустим JWT или серверная session-модель.

Обязательные свойства независимо от реализации:

- credential не хранится во Frontend в `localStorage`;
- должен существовать механизм logout;
- заблокированный пользователь теряет доступ;
- после reset/change password должна существовать возможность инвалидировать старые активные сессии;
- секреты не попадают в URL.

Предпочтительный вариант для web MVP: защищённая `HttpOnly` cookie.

---

# 12. RBAC

На Этапе 1:

`DIRECTOR`
- полный пользовательский доступ внутри своего сада;
- позднее сможет создавать ADMIN и управлять критическими настройками.

`ADMIN`
- операционная роль;
- не может назначить себя DIRECTOR;
- не может управлять чужой организацией.

Обязательное правило:

> Frontend никогда не является источником истины для прав доступа.

Каждый защищённый Backend endpoint проверяет пользователя и роль самостоятельно.

---

# 13. Tenant isolation

Это критическое требование.

Пользователь организации A никогда не должен получать данные организации B.

Нельзя доверять:

```text
organization_id
```

который прислал клиент.

`organization_id` текущего пользователя определяется сервером из authenticated context.

## Обязательный негативный тест

1. Создать Organization A.
2. Создать Organization B.
3. Создать пользователя A.
4. Попробовать обратиться от пользователя A к ресурсу B.
5. Получить `403` или `404` согласно утверждённой политике.
6. Данные B не должны попасть в response body или logs.

---

# 14. Создание первоначальных пользователей

Для dev окружения сделать seed-команду или другой безопасный способ создать:

```text
Organization: Детский сад «Солнышко»

DIRECTOR:
username: director-demo

ADMIN:
username: admin-demo
```

Пароли не коммитить в репозиторий.

Использовать только синтетические данные.

---

# 15. API ошибки

Единый формат:

```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Неверный логин или пароль",
    "field": null
  }
}
```

`field` используется только когда ошибка относится к конкретному полю.

Не возвращать:

- stack trace;
- SQL ошибки;
- секреты;
- внутренние пути сервера.

---

# 16. Коды ошибок Этапа 1

Минимально:

```text
INVALID_CREDENTIALS
USER_BLOCKED
ORGANIZATION_BLOCKED
PASSWORD_CHANGE_REQUIRED
INVALID_PASSWORD
USERNAME_ALREADY_EXISTS
UNAUTHORIZED
FORBIDDEN
VALIDATION_ERROR
INTERNAL_ERROR
```

---

# 17. Password policy

Для MVP определить минимум:

- длина не менее 10 символов;
- временный пароль генерируется системой;
- новый пароль не должен совпадать с временным текущим паролем;
- максимальную длину также валидировать;
- не обрезать пароль незаметно.

Сложные требования вида «обязательная спецбуква + цифра + заглавная» не вводить без необходимости.

---

# 18. Валидация

Backend обязан проверять:

- username;
- password;
- status пользователя;
- status организации;
- роль;
- `must_change_password`;
- принадлежность пользователя организации.

Нельзя рассчитывать на Frontend validation.

---

# 19. Логирование

На Этапе 1 разрешено логировать:

- технический request id;
- endpoint;
- HTTP status;
- длительность запроса;
- user id после авторизации;
- organization id после авторизации.

Не логировать:

- password;
- temporary password;
- password_hash;
- полный request body login/change-password.

---

# 20. Персональные данные

Этап 1 должен проектироваться так, чтобы дальнейшая система соответствовала принципу минимизации данных.

Требования:

- не использовать реальные ФИО детей/родителей;
- dev/test только на синтетических данных;
- исключить секреты и ПДн из технических логов;
- production размещение данных проектировать в РФ;
- изоляция организаций обязательна;
- доступ к данным только по роли и необходимости.

Юридическая модель оператора/обработчика будет утверждаться отдельно до пилота.

---

# 21. Миграции

Alembic должен уметь:

```text
upgrade head
downgrade
```

Минимальные миграции:

1. organization
2. user

Приложение не должно создавать production tables через `create_all()` при старте.

---

# 22. Тесты

Минимальный набор автоматических тестов:

### Auth
- успешный login;
- неправильный password;
- неизвестный username;
- blocked user;
- blocked organization;
- must_change_password;
- успешная смена пароля;
- старый пароль не работает;
- logout.

### Permissions
- endpoint без auth → 401;
- ADMIN не получает DIRECTOR-only permission;
- пользователь A не получает данные organization B.

### Security
- password_hash не возвращается API;
- temporary password не сохраняется как plaintext;
- login password не появляется в logs тестового обработчика.

---

# 23. OpenAPI

FastAPI `/docs` должен отражать реальный API.

Для каждого endpoint:

- request schema;
- response schema;
- возможные ошибки;
- auth requirement.

---

# 24. Что НЕ делать на Этапе 1

Не реализовывать:

- Child;
- Guardian;
- Group;
- Attendance;
- Employee business module;
- Announcement;
- Dashboard;
- PARENT UI;
- TEACHER;
- СКУД;
- планшет;
- фото;
- документы;
- платежи;
- AI.

---

# 25. Порядок работы

## BACK-01
Инициализация проекта, config, PostgreSQL.

## BACK-02
Organization model + migration.

## BACK-03
User model + migration.

## BACK-04
Password hashing + temporary password generator.

## BACK-05
Login/logout.

## BACK-06
`/auth/me`.

## BACK-07
Mandatory password change.

## BACK-08
RBAC.

## BACK-09
Tenant isolation guard.

## BACK-10
Seed demo data.

## BACK-11
Tests.

## BACK-12
OpenAPI + Backend README.

---

# 26. Definition of Done

Этап 1 Backend считается завершённым, когда:

- приложение поднимается с чистой БД;
- миграции проходят;
- DIRECTOR может войти;
- ADMIN может войти;
- временный пароль заставляет пользователя установить новый;
- старый пароль после смены не работает;
- `/auth/me` возвращает роль и организацию;
- blocked user не работает;
- blocked organization не работает;
- Backend не доверяет `organization_id` от клиента;
- тест tenant isolation проходит;
- секреты не попадают в Git;
- тесты зелёные;
- OpenAPI актуален;
- Frontend-разработчик может подключить login без уточнения форматов.

---

# 27. Результат для передачи команде

Backend-разработчик передаёт:

1. работающий backend;
2. `.env.example`;
3. миграции;
4. seed-инструкцию;
5. URL локального API;
6. актуальный OpenAPI;
7. список реализованных endpoint;
8. тестовые учётные записи без публикации production-секретов;
9. README запуска.

После этого Backend может начинать Этап 2.
