# Умный сад — мастер-черновик проекта

> Статус: живой черновик / база знаний проекта.  
> Этот документ фиксирует принятые решения, логику продукта, архитектуру, роли, ограничения, этапы и организацию разработки.  
> Он нужен для того, чтобы в будущем не восстанавливать контекст по переписке и не принимать противоречащие решения заново.

---

# 1. Что это за проект

**Название:** «Умный сад»

**Тип продукта:** SaaS / операционная система для частных детских садов.

**Идея:** создать единую цифровую систему, которая связывает:
- руководство детского сада;
- администраторов;
- сотрудников;
- родителей;
- в будущем — систему контроля доступа и другие сервисы.

Цель — заменить набор разрозненных таблиц, чатов, бумажных журналов и ручных процессов одной понятной системой.

Проект изначально строится как **масштабируемый SaaS**, а не как отдельная кастомная программа под один детский сад.

---

# 2. Базовая продуктовая идея

Система должна стать «операционной системой» частного детского сада.

Внутри одной системы в перспективе могут быть:
- управление детским садом;
- дети;
- группы;
- родители / законные представители;
- сотрудники;
- посещаемость;
- объявления;
- расписание;
- питание;
- платежи;
- фотографии;
- аналитика;
- управление сетью садов;
- доступ через турникеты / СКУД;
- планшет на входе;
- дополнительные интеграции;
- AI-функции.

Но **не всё это входит в первый MVP**.

Главный принцип: сначала собрать небольшой, понятный, безопасный фундамент, после чего расширять систему модулями.

---

# 3. Основные принципы продукта

## 3.1. Минимум технической сложности для детского сада

В каждом саду не должен быть нужен отдельный IT-администратор.

Операционные настройки выполняет:
- DIRECTOR;
- ADMIN.

Техническое администрирование платформы выполняет команда «Умного сада».

## 3.2. Минимизация человеческого фактора

Интерфейс должен быть понятным человеку без технической подготовки.

Необходимо избегать:
- сложных ручных настроек;
- лишних обязательных полей;
- дублирования информации;
- ситуаций, когда администратор должен понимать устройство базы данных или инфраструктуры.

## 3.3. SaaS, а не кастомная разработка под каждого клиента

Целевой принцип:
- 80–90% системы одинаково для всех садов;
- различия решаются настройками;
- не создавать отдельную ветку продукта под каждого клиента.

## 3.4. Tenant isolation

Каждый детский сад — отдельный tenant / Organization.

Данные одного сада не должны быть доступны другому саду ни при каких обстоятельствах.

## 3.5. Не удалять историю без необходимости

Для:
- детей;
- групп;
- сотрудников;
- родителей / guardians;

предпочтение отдаётся:
- archive;
- soft delete;
- деактивации связи;

а не физическому удалению строки из базы.

## 3.6. Backend — источник истины по безопасности

Frontend может скрывать кнопки и элементы UI, но:
- это не считается защитой;
- реальные permission checks выполняет Backend.

---

# 4. Российский рынок и персональные данные

Проект ориентирован на работу с частными детскими садами в России.

Это означает, что законодательство о персональных данных должно учитываться **на уровне архитектуры**, а не добавляться в конце.

Базовая правовая рамка, которую необходимо учитывать перед реальным запуском:
- Федеральный закон №152-ФЗ «О персональных данных»;
- требования к обработке персональных данных граждан РФ;
- требования к оператору/обработчику;
- локализация данных;
- уведомления/документы/согласия;
- договорные отношения;
- хранение и удаление;
- права субъектов;
- работа с подрядчиками и внешними сервисами.

Этот документ не является юридическим заключением. Перед реальным пилотом с настоящими персональными данными обязательна отдельная юридическая и техническая проверка.

---

# 5. Правило по персональным данным

Для каждой функции нужно задавать вопросы:

1. Какие данные собираем?
2. Зачем они нужны?
3. Можно ли не собирать их вообще?
4. Кто видит эти данные?
5. Кто может их редактировать?
6. Где они хранятся?
7. Как долго хранятся?
8. Как архивируются/удаляются?
9. Логируется ли чувствительное действие?
10. Передаются ли данные третьим лицам?

## В dev/test

Разрешены только:
- синтетические данные;
- тестовые ФИО;
- выдуманные организации;
- выдуманные логины.

Запрещено использовать:
- реальные данные детей;
- реальные данные родителей;
- реальные медицинские данные;
- реальные документы;
- реальные пароли.

---

# 6. Что НЕ входит в первый MVP

В первый MVP намеренно не включаются:

- полный Parent UI;
- Teacher UI;
- платежи;
- СКУД;
- турникеты;
- планшет на входе;
- Face ID;
- биометрия;
- фотографии;
- чаты;
- медицинские данные;
- диагнозы;
- паспортные данные;
- СНИЛС;
- документы;
- AI;
- email/SMS recovery;
- внешние интеграции;
- сложная аналитика;
- питание;
- push-уведомления;
- сложный messenger.

Эти элементы не считаются отменёнными — они **отложены**.

---

# 7. СКУД / турникеты / планшет

Идея была рассмотрена как важное развитие продукта.

Основная мысль:
- в будущем можно использовать планшет/терминал на входе;
- система сможет фиксировать факт прихода/ухода;
- возможно подключение турникетов или иного оборудования;
- это может повысить уверенность родителей и администрации в том, кто действительно вошёл/вышел.

Но принято решение:

**не включать СКУД в текущий MVP.**

Причины:
- дополнительное оборудование;
- интеграции;
- монтаж;
- поддержка;
- требования безопасности;
- необходимость отдельного пилота.

СКУД рассматривается как отдельный следующий проект/модуль после стабильного программного MVP.

---

# 8. Роли

## 8.1. DIRECTOR

DIRECTOR — руководитель конкретного сада.

Может:
- видеть Dashboard;
- видеть весь свой сад;
- управлять детьми;
- управлять группами;
- управлять guardians;
- управлять сотрудниками;
- управлять посещаемостью;
- создавать объявления;
- изменять основные настройки сада;
- создавать и архивировать группы/детей;
- связывать guardians с детьми;
- создавать сотрудников;
- назначать ADMIN;
- блокировать пользователей;
- сбрасывать пароли;
- смотреть Audit Log.

Не может:
- видеть другие сады;
- становиться глобальным SUPER_ADMIN;
- управлять технической инфраструктурой платформы.

---

## 8.2. ADMIN

Операционная роль внутри сада.

Может:
- создавать/редактировать/архивировать детей;
- управлять группами;
- переводить детей между группами;
- добавлять guardians;
- создавать PARENT accounts;
- сбрасывать временный пароль родителя;
- работать с посещаемостью;
- создавать объявления;
- добавлять обычных сотрудников.

Не может:
- назначать DIRECTOR;
- повышать собственные привилегии;
- удалять Organization;
- менять критические platform settings;
- видеть другие сады.

---

## 8.3. PARENT

В полном виде Parent UI отложен.

Но уже в MVP архитектура должна учитывать, что:
- у одного ребёнка может быть несколько guardians;
- у одного guardian может быть несколько детей;
- Parent account привязан к Guardian;
- один Parent account не нужно дублировать для каждого ребёнка.

В текущем MVP PARENT нужен как:
- роль;
- User account;
- связь с Guardian;
- возможность пройти auth flow.

Полный интерфейс родителя будет позже.

---

## 8.4. TEACHER

Будущая роль.

Идея:
- видит назначенную группу/группы;
- видит только необходимые данные детей;
- не должен видеть весь сад;
- права будут минимальными.

Не входит в текущий MVP.

---

## 8.5. SUPER_ADMIN

Будущая роль платформы.

Нужна для:
- управления несколькими садами;
- поддержки;
- технического администрирования;
- контроля организаций.

Не входит в Stage 1.

---

# 9. Текущий Director/Admin UI

Меню:

- Главная
- Дети
- Группы
- Родители
- Сотрудники
- Посещаемость
- Объявления
- Настройки

На первом этапе из бизнес-разделов реально функциональна только техническая Главная.

Остальные модули добавляются по этапам.

---

# 10. Dashboard — будущая логика MVP

Dashboard должен показывать:
- активные дети;
- присутствуют сегодня;
- отсутствуют сегодня;
- нет отметки;
- сотрудники;
- статистика посещаемости по группам.

На Stage 1 Dashboard пока технический и подтверждает:
- кто вошёл;
- какая Organization;
- какая роль.

---

# 11. Child

## Основные поля

- first_name;
- last_name;
- middle_name — optional;
- birth_date;
- group;
- status.

## Список детей

Показывает:
- ФИО;
- дату рождения / возраст;
- группу;
- статус посещения сегодня;
- общий статус.

## Фильтры

- по группе;
- по статусу;
- по имени.

## Карточка ребёнка

В перспективе:
- основные данные;
- текущая группа;
- guardians;
- посещаемость;
- история изменений.

## Важное ограничение первого MVP

Не хранить:
- диагнозы;
- медицинские данные;
- паспорт;
- СНИЛС;
- биометрию;
- фотографии.

Использовать archive вместо hard delete.

---

# 12. Group

Поля:
- name;
- status;
- child count — вычисляемое/агрегируемое.

Возможности:
- создать;
- редактировать;
- архивировать;
- открыть профиль;
- посмотреть детей;
- посмотреть посещаемость за сегодня;
- перевести ребёнка между группами.

---

# 13. Guardian

Guardian — родитель/законный представитель/другое доверенное лицо.

Поля:
- first_name;
- last_name;
- middle_name — optional;
- phone — optional;
- email — optional;
- status;
- linked User — optional.

## Связь Child ↔ Guardian

Many-to-many.

В ChildGuardian:
- child_id;
- guardian_id;
- relation_type.

relation_type:
- mother;
- father;
- guardian;
- other.

Связь должна иметь историю.

Link/unlink считается чувствительным действием и должно попадать в Audit Log.

Не удалять историю отношений физически без необходимости.

---

# 14. Attendance

В MVP посещаемость ручная.

Поля:
- child;
- date;
- status;
- arrival_time — optional;
- departure_time — optional;
- comment — optional;
- created_by;
- updated_by;
- timestamps.

Status:
- present;
- absent;
- unknown.

Фильтры:
- дата;
- группа;
- ребёнок;
- статус.

Изменения посещаемости должны аудитироваться.

---

# 15. Announcements

Поля:
- title;
- text;
- author;
- target;
- timestamps.

Target:
- вся Organization;
- конкретная группа.

В первом MVP:
- без push;
- без email;
- без SMS.

---

# 16. Settings

Базовые настройки сада:
- название;
- адрес;
- телефон;
- email — optional;
- часы работы.

DIRECTOR видит больше настроек.

ADMIN — ограниченный набор.

Технические настройки платформы здесь не должны появляться.

---

# 17. Authentication

Принято решение не использовать email как обязательный login.

Основной login:
- username;
- password.

Email/phone:
- optional;
- не используются как credentials.

---

# 18. Parent account flow

Когда создаётся Parent account:

1. DIRECTOR/ADMIN создаёт или находит Guardian.
2. Guardian связывается с Child.
3. Если у Guardian ещё нет User:
   - система создаёт PARENT User;
   - генерирует username;
   - генерирует временный пароль.
4. Временный пароль показывается **один раз**.
5. `must_change_password=true`.
6. При первом входе пользователь обязан заменить пароль.
7. Старый temporary password после смены больше не работает.

Если Guardian уже связан с другим ребёнком:
- новый User не создаётся;
- используется тот же Guardian/User;
- создаётся только дополнительная ChildGuardian связь.

---

# 19. Username

Username:
- глобально unique;
- case-insensitive;
- нормализуется;
- trim spaces.

Примеры:
- `ivanova-a-4821`
- `parent-583241`

Точный генератор можно изменить позже, но принцип уникальности фиксирован.

---

# 20. Password

Пароль:
- хранится только как secure hash;
- plaintext никогда не сохраняется;
- temp password не хранится plaintext;
- temp password показывается один раз.

Минимальный пароль на Stage 1:
- 10 символов.

Подходящий hashing:
- Argon2id;
- bcrypt.

Нельзя использовать MD5/SHA256 как password hashing.

---

# 21. Password reset

На первом MVP нет:
- email reset;
- SMS reset.

Recovery flow:

1. родитель обращается в сад;
2. сад проверяет личность организационным способом;
3. DIRECTOR/ADMIN выполняет reset;
4. система генерирует новый temporary password;
5. старый пароль становится недействительным;
6. `must_change_password=true`.

DIRECTOR/ADMIN не может увидеть старый пароль пользователя.

---

# 22. Общая архитектура приложения

```text
Browser
   ↓
Frontend
Next.js + React + TypeScript
   ↓
HTTP / JSON
/api/v1
   ↓
Backend
FastAPI + Python
   ↓
SQLAlchemy + Alembic
   ↓
PostgreSQL
```

Это единая архитектура.

---

# 23. Главное правило по базе данных

**Единственная основная БД MVP — PostgreSQL.**

Frontend:
- не имеет собственной БД;
- не использует SQLite;
- не использует Firebase;
- не использует Supabase;
- не подключается напрямую к PostgreSQL.

Frontend работает только через Backend API.

Backend работает с PostgreSQL.

Это правило принято специально, чтобы Backend и Frontend не превратились в два несовместимых проекта.

---

# 24. Backend stack

Зафиксировано:

- Python 3.12+
- FastAPI
- PostgreSQL
- SQLAlchemy 2.x
- Alembic
- Pydantic
- pydantic-settings
- pytest
- httpx

---

# 25. Frontend stack

Зафиксировано:

- Next.js
- React
- TypeScript
- единый API client

Backend base path:
- `/api/v1`

---

# 26. Локальные адреса Stage 1

Frontend:
- `http://localhost:3000`

Backend:
- `http://localhost:8000`

API:
- `http://localhost:8000/api/v1`

PostgreSQL DB:
- `smart_garden`

Frontend env:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

Backend dev CORS:
- `http://localhost:3000`

---

# 27. Session / auth architecture

Для web MVP принято ориентироваться на:
- HttpOnly cookie.

Frontend:
- делает запросы с credentials;
- не хранит auth token в localStorage/sessionStorage.

Production cookie:
- Secure;
- HttpOnly;
- соответствующие SameSite настройки.

Local development может использовать HTTP.

Logout завершает текущую session.

После password reset/change старые credentials/sessions должны инвалидироваться в соответствии с выбранной реализацией.

---

# 28. API contract Stage 1

Base path:
- `/api/v1`

Endpoints:

- `GET /api/v1/health`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/change-password`

JSON:
- snake_case.

Дата/время:
- ISO 8601;
- UTC на API/Backend.

---

# 29. Error format

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

Основные Stage 1 codes:
- INVALID_CREDENTIALS
- USER_BLOCKED
- ORGANIZATION_BLOCKED
- PASSWORD_CHANGE_REQUIRED
- INVALID_PASSWORD
- USERNAME_ALREADY_EXISTS
- UNAUTHORIZED
- FORBIDDEN
- VALIDATION_ERROR
- INTERNAL_ERROR

Frontend не показывает:
- stack trace;
- raw exception;
- внутренние технические сообщения.

---

# 30. HTTP statuses

Принята ориентировочная политика:

- 200 — success;
- 201 — resource created;
- 400 — business/application validation;
- 401 — unauthenticated;
- 403 — forbidden;
- 404 — not found;
- 409 — conflict;
- 500 — unexpected server error.

Backend должен нормализовать validation errors так, чтобы Frontend не угадывал разные форматы.

---

# 31. Tenant isolation

Organization context:
- определяется сервером;
- берётся из authenticated User/session;
- не доверяет `organization_id`, присланному клиентом.

Обязательный negative test:

```text
Organization A
  User A

Organization B
  Resource B

User A НЕ получает Resource B
```

Это один из критических security тестов проекта.

---

# 32. Audit Log

Audit Log обязателен для чувствительных действий.

В будущем/по мере появления сущностей логировать:
- создание пользователя;
- блокировку;
- reset password;
- изменение роли;
- link/unlink Guardian ↔ Child;
- изменение attendance;
- archive;
- критические settings changes.

Нельзя логировать:
- password;
- hash;
- temporary password;
- лишние персональные данные.

---

# 33. Organization model

Поля:
- id;
- name;
- status;
- created_at;
- updated_at.

Status:
- active;
- blocked;
- archived.

Organization — основа multi-tenant архитектуры.

---

# 34. User model

Поля Stage 1:
- id;
- organization_id;
- username;
- password_hash;
- role;
- status;
- must_change_password;
- created_at;
- updated_at;
- last_login_at.

Stage 1 roles:
- DIRECTOR;
- ADMIN.

Status:
- active;
- blocked;
- archived.

---

# 35. Repository

GitHub repository:

`ONN9IX/smart-garden`

Owner:
- ONN9IX

Collaborators:
- ONN9IX
- F1zname

---

# 36. Команда

## ONN9IX

Роль в разработке:
- Frontend.

Владелец репозитория.

## F1zname

Роль:
- Backend.

Уровень:
- начинающий разработчик.

Поэтому Backend Issues должны быть максимально подробными и вести разработчика по шагам.

---

# 37. Принцип разделения работы

Не делить проект по пользовательским ролям.

Нельзя делать:
- «ты делаешь Director, я делаю Parent».

Причина:
- общие сущности;
- общая авторизация;
- общая БД;
- общие permissions;
- одна архитектура.

Принято разделение:
- Backend/Core — F1zname;
- Frontend/UX — ONN9IX.

---

# 38. Git workflow

`main` — стабильная общая ветка.

Не вести основную разработку напрямую в `main`.

Для каждой Issue:

```text
fresh main
   ↓
отдельная branch
   ↓
code
   ↓
test
   ↓
push
   ↓
Pull Request
   ↓
review
   ↓
merge main
   ↓
следующая Issue
```

---

# 39. Branch naming

Backend:
- `backend/BACK-01-init`
- `backend/BACK-02-organization`
- и т.д.

Frontend:
- `frontend/FRONT-01-init`
- `frontend/FRONT-02-api-client`
- и т.д.

---

# 40. Структура репозитория

Целевая:

```text
smart-garden/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── services/
│   ├── tests/
│   ├── alembic/
│   ├── alembic.ini
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── .env.example
│
├── docs/
├── .gitignore
└── README.md
```

Backend не должен случайно редактировать Frontend.

Frontend не должен случайно строить собственный backend/database layer.

---

# 41. Этап 1 — фундамент

Backend:
- Organization;
- User;
- roles;
- username/password auth;
- temporary password;
- mandatory password change;
- RBAC;
- tenant isolation;
- demo seed;
- tests;
- OpenAPI.

Frontend:
- app foundation;
- API client;
- UI components;
- Login;
- auth state;
- password change;
- protected routes;
- AppShell;
- role-aware UI;
- technical Dashboard;
- common error/loading states;
- responsive.

Общий результат:
- DIRECTOR/ADMIN входит;
- меняет temporary password;
- видит свою Organization;
- попадает на Dashboard;
- logout работает.

---

# 42. Backend Stage 1 порядок

Строго:

1. BACK-01 — FastAPI + PostgreSQL + health
2. BACK-02 — Organization
3. BACK-03 — User
4. BACK-04 — password hashing + temp password
5. BACK-05 — login/logout
6. BACK-06 — /auth/me
7. BACK-07 — mandatory password change
8. BACK-08 — RBAC
9. BACK-09 — tenant isolation
10. BACK-10 — demo seed
11. BACK-11 — tests
12. BACK-12 — OpenAPI + README

Не переходить к children/groups/guardians до завершения Stage 1.

---

# 43. Frontend Stage 1 порядок

Строго:

1. FRONT-01 — Next.js + TypeScript
2. FRONT-02 — API client
3. FRONT-03 — UI components
4. FRONT-04 — Login
5. FRONT-05 — auth state + /auth/me
6. FRONT-06 — password change
7. FRONT-07 — protected routes
8. FRONT-08 — AppShell
9. FRONT-09 — role-aware UI
10. FRONT-10 — technical Dashboard
11. FRONT-11 — error/loading/empty states
12. FRONT-12 — responsive + logout + README

---

# 44. Stage 1 integration checkpoint

Stage 1 нельзя считать завершённым отдельно по Backend и Frontend.

Нужен единый сценарий:

```text
PostgreSQL ON
   ↓
Backend :8000
   ↓
Frontend :3000
   ↓
Login temporary credentials
   ↓
Backend checks PostgreSQL
   ↓
must_change_password=true
   ↓
Frontend → change-password
   ↓
Backend saves new hash
   ↓
old temporary password invalid
   ↓
GET /auth/me
   ↓
Dashboard
   ↓
Logout
```

Без этого Stage 1 не завершён.

Создана отдельная GitHub Issue:
- INTEGRATION-01 (#27)

---

# 45. Stage 2 — Groups / Children / Guardians / Parent accounts

## Backend

Добавить:
- Group;
- Child;
- Guardian;
- ChildGuardian;
- PARENT account;
- generated username;
- temporary password;
- reset temporary password.

## Frontend

Добавить:
- группы;
- дети;
- родители/guardians;
- карточки;
- формы;
- фильтры;
- связи.

## Первый вертикальный бизнес-сценарий

```text
DIRECTOR login
   ↓
создаёт Group
   ↓
создаёт Child
   ↓
добавляет Guardian
   ↓
создаёт PARENT account
   ↓
получает username + temporary password
   ↓
Child виден в Group
```

Это первый большой продуктовый checkpoint после auth foundation.

---

# 46. Stage 3 — Employees + Attendance

## Employees

DIRECTOR:
- создаёт сотрудников;
- назначает допустимые роли;
- блокирует;
- reset password.

ADMIN:
- может добавлять обычных сотрудников;
- не может назначить DIRECTOR.

## Attendance

Manual attendance:
- present;
- absent;
- unknown.

Дополнительно:
- arrival_time;
- departure_time;
- comment.

---

# 47. Stage 4 — Announcements + Dashboard + Audit

Добавить:
- announcements;
- group targeting;
- organization targeting;
- реальный Dashboard;
- Audit Log;
- стабилизацию.

---

# 48. Stage 5 — подготовка к пилоту

До реального пилота:
- integration tests;
- security tests;
- tenant tests;
- backup/restore;
- production configuration;
- monitoring;
- documentation;
- personal-data checklist;
- test garden;
- обучение пользователя;
- юридическая проверка;
- production infrastructure review.

Реальные данные детей не должны попадать в систему до этого этапа.

---

# 49. Demo environment

Для разработки используется synthetic Organization:

**Детский сад «Солнышко»**

Users:
- `director-demo`
- `admin-demo`

Пароли:
- не хранить в Git;
- не писать в README;
- получать/создавать безопасно через dev flow.

---

# 50. Backend logs

Можно логировать:
- request_id;
- endpoint;
- HTTP status;
- duration;
- user_id;
- organization_id.

Нельзя логировать:
- password;
- password_hash;
- temporary password;
- auth request body;
- лишние персональные данные.

---

# 51. OpenAPI

Backend должен поддерживать актуальную OpenAPI документацию.

Frontend не должен «угадывать» Backend.

Если контракт расходится:
1. открыть `docs/03-api-contract-v0.1.md`;
2. понять, какая сторона нарушила контракт;
3. исправить эту сторону;
4. если нужен новый контракт — сначала обновить документ;
5. после этого обновить Backend и Frontend.

---

# 52. Работа с mocks

Frontend может временно использовать mocks.

Но:
- mock должен **полностью совпадать** с реальным API contract;
- нельзя придумывать альтернативные поля;
- после появления Backend endpoint mock удаляется/заменяется на реальный запрос.

---

# 53. Что делать, если разработчик не понимает задачу

Порядок:

1. открыть GitHub Issue;
2. открыть `docs/00-development-guide.md`;
3. открыть stage-specific doc;
4. открыть `docs/03-api-contract-v0.1.md`;
5. открыть этот master draft;
6. только потом задавать вопрос.

Нельзя самостоятельно менять:
- БД;
- стек;
- API;
- JSON format;
- auth;
- role logic;
- tenant model;
- data model;
- personal-data scope.

---

# 54. Definition of Done каждой задачи

Issue считается готовой только если:
- код запускается;
- все пункты Issue выполнены;
- предыдущий функционал не сломан;
- secrets отсутствуют;
- реальные персональные данные отсутствуют;
- нет второй БД;
- API соответствует contract;
- есть commit;
- есть PR;
- PR проверен;
- изменения merged в `main`.

---

# 55. Чего нельзя делать ради скорости

Нельзя:
- выключать tenant isolation;
- пропускать permission checks;
- пропускать password security;
- хранить plaintext password;
- отказываться от tests для security;
- давать Frontend прямой доступ к БД;
- брать реальные детские данные для «удобства тестирования»;
- начинать новые большие модули до завершения foundation.

---

# 56. Почему Backend описан особенно подробно

Backend-разработчик F1zname — начинающий.

Поэтому подход:
- не просто «реализовать FastAPI»;
- а конкретно объяснять:
  - что установить;
  - что открыть;
  - какую ветку выбрать;
  - какую папку создать;
  - какие зависимости поставить;
  - какие файлы создать;
  - что проверить;
  - что нельзя делать;
  - как commit/push/PR;
  - что считается готовым.

Цель — чтобы Issue сама вела разработчика по работе.

---

# 57. Почему Frontend и Backend интегрированы в одном плане

Была выявлена ключевая проблема:

если Backend самостоятельно выберет PostgreSQL, а Frontend начнёт создавать SQLite/собственную БД, проект распадётся на две несовместимые системы.

Поэтому принято:
- единая архитектура;
- единая база;
- единый API;
- единые conventions;
- единый stage plan;
- общая integration Issue.

---

# 58. Текущие рабочие ветки

Уже созданы:

- `backend/BACK-01-init`
- `frontend/FRONT-01-init`

Они созданы от `main`.

---

# 59. Текущие ответственные

Backend Issues BACK-01 → BACK-12:
- F1zname.

Frontend Issues FRONT-01 → FRONT-12:
- ONN9IX.

SHARED-01:
- ONN9IX + F1zname.

INTEGRATION-01:
- ONN9IX + F1zname.

---

# 60. Что делать прямо сейчас

## F1zname

1. Прочитать:
   - README;
   - `docs/00-development-guide.md`;
   - `docs/01-stage-1-backend.md`;
   - `docs/03-api-contract-v0.1.md`;
   - `docs/05-personal-data-baseline.md`;
   - этот master draft.
2. Проверить SHARED-01.
3. Переключиться на `backend/BACK-01-init`.
4. Выполнить BACK-01 пошагово.
5. Создать PR.
6. Не начинать BACK-02 до merge.

## ONN9IX

1. Прочитать:
   - README;
   - `docs/00-development-guide.md`;
   - `docs/02-stage-1-frontend.md`;
   - `docs/03-api-contract-v0.1.md`;
   - `docs/05-personal-data-baseline.md`;
   - этот master draft.
2. Проверить SHARED-01.
3. Переключиться на `frontend/FRONT-01-init`.
4. Выполнить FRONT-01.
5. Создать PR.
6. Не начинать FRONT-02 до merge.

---

# 61. Что будет после первого MVP

Возможные направления:
- Parent app/UI;
- Teacher UI;
- сети детских садов;
- СКУД;
- планшет на входе;
- турникеты;
- уведомления;
- платежи;
- питание;
- фото;
- занятия;
- расширенная аналитика;
- AI;
- автоматизация коммуникации;
- отчёты;
- мобильные приложения.

Решение о порядке этих модулей принимается после MVP и первых пилотов.

---

# 62. Принцип будущего развития

Каждая новая функция должна отвечать минимум на три вопроса:

1. Какую реальную проблему детского сада она решает?
2. Нужна ли она большинству клиентов или это единичный кастомный запрос?
3. Какие новые риски по персональным данным/безопасности она создаёт?

Если функция сложная, но не даёт очевидной ценности — не включать её рано.

---

# 63. Главное правило проекта

**Не строить много функций одновременно.**

Правильный путь:

```text
Foundation
   ↓
Groups + Children + Guardians
   ↓
Employees + Attendance
   ↓
Announcements + Dashboard + Audit
   ↓
Pilot readiness
   ↓
Real pilot
   ↓
Access control / Parent UI / other modules
```

---

# 64. Документы в репозитории

- `docs/00-development-guide.md` — главная рабочая инструкция команды.
- `docs/01-stage-1-backend.md` — Stage 1 Backend.
- `docs/02-stage-1-frontend.md` — Stage 1 Frontend.
- `docs/03-api-contract-v0.1.md` — API contract.
- `docs/04-mvp-roadmap.md` — дорожная карта MVP.
- `docs/05-personal-data-baseline.md` — baseline по персональным данным.
- `docs/06-product-scope.md` — рамки продукта.
- `docs/07-project-master-draft.md` — этот документ: полный черновой контекст проекта.

---

# 65. Как использовать этот файл

Это не финальная спецификация и не юридический документ.

Это:
- память проекта;
- черновой журнал решений;
- защита от потери контекста;
- onboarding document;
- источник для будущих ТЗ;
- место, куда нужно добавлять новые принятые решения.

Если новое решение меняет старое:
- старое не стирать бесследно;
- желательно добавить раздел «Изменено» или отметить причину;
- затем синхронизировать рабочие ТЗ и Issues.

---

# 66. Текущий статус

На данный момент:
- продуктовая идея определена;
- MVP scope определён;
- роли определены;
- Stage 1 архитектура определена;
- Backend/Frontend stack определён;
- PostgreSQL зафиксирован;
- API foundation определён;
- GitHub repo настроен;
- F1zname получил Write access;
- задачи распределены;
- Backend Issues детализированы;
- Frontend Issues детализированы;
- стартовые ветки созданы;
- integration Issue создана;
- разработка Stage 1 может начинаться.

---

# 67. Краткая формула проекта

```text
Умный сад =
SaaS для частных детских садов
+ единый кабинет управления
+ строгая изоляция данных
+ минимальный сбор ПДн
+ понятные роли
+ простой UX
+ PostgreSQL
+ FastAPI
+ Next.js
+ модульное развитие
+ в будущем СКУД/планшет/турникеты
```

---

# 68. Правило обновления master draft

После каждого существенного решения рекомендуется обновлять этот файл.

Примеры существенных решений:
- изменение MVP scope;
- новая роль;
- изменение БД;
- изменение auth;
- новый stage;
- новая архитектура;
- изменение data model;
- новая интеграция;
- новая hardware часть;
- изменение персональных данных;
- изменение команды/ответственности.

Этот файл должен оставаться понятным человеку, который не читал ни одного сообщения проекта.
