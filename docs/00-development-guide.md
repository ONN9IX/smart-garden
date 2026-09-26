# Единая инструкция разработки — Умный сад MVP 0.1

> Это главный рабочий документ команды. Если отдельная Issue противоречит этому документу или `docs/03-api-contract-v0.1.md`, сначала остановиться и согласовать изменение. Не придумывать собственный стек, БД, поля API или способ авторизации.

## 1. Кто что делает

Роли Frontend/Backend назначаются **на конкретный этап** и могут меняться между разработчиками.

**Stage 1:**
- **ONN9IX — Frontend.**
- **F1zname — Backend.**

Планируемый принцип следующих этапов: разработчики меняются ролями, чтобы оба могли работать с обеими частями системы. Поэтому никакой компонент не должен зависеть от личного пароля, локального файла или окружения одного человека.

Правила доступов и смены ролей: `docs/08-team-access-and-environments.md`.

- Репозиторий один: `ONN9IX/smart-garden`.
- `main` — общая стабильная ветка. Напрямую разработку в `main` не вести.
- Каждая Issue выполняется в отдельной ветке и попадает в `main` через Pull Request.

## 2. Главное правило интеграции

Frontend и Backend — две части ОДНОГО приложения, а не два независимых проекта.

Единая цепочка данных:

```text
Браузер пользователя
        |
        v
Frontend: Next.js + React + TypeScript
        |
        | HTTP / JSON, только /api/v1/*
        v
Backend: FastAPI + Python
        |
        | SQLAlchemy + Alembic
        v
PostgreSQL
```

### Запрещено

- Frontend не подключается напрямую к PostgreSQL.
- Frontend не использует SQLite, Supabase, Firebase или другую отдельную БД.
- Backend не заменяет PostgreSQL на SQLite "для удобства".
- Не создавать второй независимый API.
- Не менять названия полей API только на одной стороне.
- Не хранить пароли, временные пароли или токены в коде.
- Не использовать реальные данные детей/родителей в разработке.

**Единственная БД проекта на MVP — PostgreSQL.**
Frontend получает и изменяет данные только через Backend API.

## 3. Технологии зафиксированы

### Backend
- Python 3.12+
- FastAPI
- PostgreSQL
- SQLAlchemy 2.x
- Alembic
- Pydantic
- pytest
- Ruff

### Frontend
- Next.js
- React
- TypeScript
- единый API client
- Backend API base path: `/api/v1`

Не менять стек без отдельного согласования.

## 4. Структура репозитория

Целевая структура:

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

Backend-разработчик работает внутри `backend/`.
Frontend-разработчик работает внутри `frontend/`.
Общие документы находятся в `docs/`.

## 5. Правило Git для новичка

Перед каждой новой задачей:

```bash
git checkout main
git pull origin main
```

Для первой задачи ветки уже созданы в GitHub. Подключиться к ним:

Backend:

```bash
git fetch origin
git checkout -b backend/BACK-01-init --track origin/backend/BACK-01-init
```

Frontend:

```bash
git fetch origin
git checkout -b frontend/FRONT-01-init --track origin/frontend/FRONT-01-init
```

Для последующих задач создавать новую ветку от свежего `main`.

После изменений:

```bash
git status
git add .
git commit -m "BACK-01: initialize backend"
git push -u origin backend/BACK-01-init
```

Для Frontend использовать соответствующий номер `FRONT-XX`.

После push создать Pull Request в `main`. Не продолжать следующую Issue в старой ветке. После merge следующая задача начинается снова от обновлённого `main`.

## 6. Как не допустить расхождения Frontend и Backend

Источник истины по API: `docs/03-api-contract-v0.1.md`.

Перед реализацией любого запроса оба разработчика проверяют:
1. HTTP method.
2. URL.
3. request JSON.
4. response JSON.
5. названия полей.
6. типы полей.
7. HTTP status.
8. error code.

Например, если Backend возвращает:

```json
{
  "user": {
    "id": "uuid",
    "username": "director-demo",
    "role": "DIRECTOR",
    "status": "active",
    "must_change_password": true
  },
  "organization": {
    "id": "uuid",
    "name": "Детский сад «Солнышко»"
  }
}
```

Frontend использует именно эти поля. Нельзя самостоятельно переименовать `must_change_password` в `needChangePassword` в сетевом контракте. Внутреннее преобразование допустимо только после получения ответа, если действительно нужно.

## 7. Порядок Этапа 1

### Шаг 0 — общий

Оба разработчика читают:
- `README.md`
- `docs/00-development-guide.md`
- `docs/01-stage-1-backend.md`
- `docs/02-stage-1-frontend.md`
- `docs/03-api-contract-v0.1.md`
- `docs/05-personal-data-baseline.md`
- `docs/08-team-access-and-environments.md`
- `docs/09-code-and-error-standards.md`

Затем закрывается SHARED-01 после подтверждения контракта.

### Backend — F1zname

Выполнять строго по порядку:

1. BACK-01 — каркас FastAPI + PostgreSQL + health.
2. BACK-02 — Organization.
3. BACK-03 — User.
4. BACK-04 — hashing + временный пароль.
5. BACK-05 — login/logout.
6. BACK-06 — /auth/me.
7. BACK-07 — обязательная смена пароля.
8. BACK-08 — RBAC.
9. BACK-09 — tenant isolation.
10. BACK-10 — synthetic seed.
11. BACK-11 — тесты.
12. BACK-12 — OpenAPI + README.

Не перескакивать к детям, группам или родителям.

### Frontend — ONN9IX

Выполнять строго по порядку:

1. FRONT-01 — Next.js + TypeScript.
2. FRONT-02 — единый API client.
3. FRONT-03 — базовые UI-компоненты.
4. FRONT-04 — Login.
5. FRONT-05 — auth state + /auth/me.
6. FRONT-06 — смена временного пароля.
7. FRONT-07 — protected routes.
8. FRONT-08 — AppShell.
9. FRONT-09 — role-aware UI.
10. FRONT-10 — технический Dashboard.
11. FRONT-11 — error/loading/empty states.
12. FRONT-12 — responsive + logout + README.

## 8. BACK-01 — инструкция для F1zname буквально по шагам

### Результат задачи

После BACK-01 должно выполняться всё:
- папка `backend/` существует;
- Python-проект запускается;
- FastAPI запускается;
- PostgreSQL используется как БД;
- приложение умеет подключаться к PostgreSQL;
- `GET /api/v1/health` возвращает `{"status":"ok"}`;
- секреты не попали в Git;
- есть `.env.example`;
- есть инструкция запуска;
- создан PR.

### 8.1 Подготовка

Установить:
- Git;
- Python 3.12 или новее;
- Docker Desktop / Docker Engine с Docker Compose;
- редактор кода.

Проверить в терминале:

```bash
git --version
python --version
docker --version
docker compose version
```

Если команда не работает — не идти дальше, сначала исправить установку.

Локальную PostgreSQL не нужно настраивать вручную: стандартная dev-БД проекта поднимается из корневого `docker-compose.yml`.

### 8.2 Получить проект

```bash
git clone https://github.com/ONN9IX/smart-garden.git
cd smart-garden
git fetch origin
git checkout main
git pull origin main
git checkout -b backend/BACK-01-init --track origin/backend/BACK-01-init
```

Проверить:

```bash
git branch
```

Активной должна быть `backend/BACK-01-init`.

### 8.3 Создать Backend

Из корня репозитория:

```bash
mkdir backend
cd backend
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Установить зависимости:

```bash
pip install fastapi uvicorn sqlalchemy psycopg[binary] alembic pydantic-settings pytest httpx ruff
pip freeze > requirements.txt
```

### 8.4 Создать структуру

Создать:

```text
backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── api/
│   │   └── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py
│   ├── db/
│   │   ├── __init__.py
│   │   └── session.py
│   ├── models/
│   │   └── __init__.py
│   ├── schemas/
│   │   └── __init__.py
│   └── services/
│       └── __init__.py
├── tests/
├── .env.example
├── requirements.txt
└── README.md
```

### 8.5 Environment

`.env.example`:

```env
APP_ENV=development
DATABASE_URL=postgresql+psycopg://smart_garden:smart_garden_local_only@localhost:5432/smart_garden
SECRET_KEY=CHANGE_ME_LOCAL
AUTH_SESSION_TTL_SECONDS=3600
CORS_ORIGINS=http://localhost:3000
```

Создать локальный `.env` на основе примера. `DATABASE_URL` для стандартной local dev-БД одинаков у всей команды. Для `SECRET_KEY` каждый разработчик задаёт своё локальное значение — его не нужно спрашивать у другого разработчика. `.env` никогда не коммитить.

Проверить корневой `.gitignore`. В нём должны игнорироваться как минимум:
```text
.env
backend/.env
backend/.venv/
__pycache__/
.pytest_cache/
node_modules/
.next/
```

### 8.6 PostgreSQL

Из **корня репозитория** запустить:

```bash
docker compose up -d postgres
```

Стандартные local dev параметры уже зафиксированы в `docker-compose.yml`:
- database: `smart_garden`;
- user: `smart_garden`;
- password: `smart_garden_local_only`;
- host: `localhost`;
- port: `5432`.

Это dev-only credential для локального контейнера с синтетическими данными, а не production secret.

Проверить:

```bash
docker compose ps
```

Контейнер `smart-garden-postgres` должен перейти в healthy/running.

**Не создавать SQLite-файл. Не использовать `sqlite:///...`. Не просить пароль локальной БД у другого разработчика.**

### 8.7 Конфигурация приложения

`app/core/config.py` должен читать настройки из environment/.env через `pydantic-settings`.

`app/db/session.py` должен создавать SQLAlchemy engine на основании `DATABASE_URL`.

Никакой DATABASE_URL не писать напрямую в Python-файле.

### 8.8 Health endpoint

В `app/main.py` создать FastAPI application и endpoint:

```text
GET /api/v1/health
```

Ответ:
```json
{"status":"ok"}
```

Запуск из `backend/`:

```bash
uvicorn app.main:app --reload --no-access-log
```

Проверить:
- Swagger открывается на `/docs`;
- `/api/v1/health` отвечает 200;
- в терминале нет traceback.

### 8.9 Проверка PostgreSQL

BACK-01 считается выполненным только если приложение действительно может создать соединение с PostgreSQL. Недостаточно просто установить пакет драйвера.

Сделать минимальную техническую проверку соединения при тесте/локальном запуске. Если PostgreSQL выключен или DATABASE_URL неверный, разработчик должен увидеть понятную ошибку подключения.

### 8.10 Перед commit

Выполнить:

```bash
git status
```

Убедиться:
- `.env` отсутствует среди staged/untracked для коммита;
- `.venv` отсутствует;
- нет паролей;
- нет SQLite-файлов;
- изменения только по BACK-01.

Запустить приложение ещё раз и проверить health.

### 8.11 Commit и Pull Request

Из корня репозитория:

```bash
git add .
git commit -m "BACK-01: initialize FastAPI and PostgreSQL"
git push -u origin backend/BACK-01-init
```

Создать PR:
- base: `main`
- compare: `backend/BACK-01-init`
- title: `BACK-01: initialize backend`
- в описании указать `Closes #2`;
- написать, как локально запустить Backend;
- подтвердить, что используется PostgreSQL.

До merge не начинать BACK-02.

## 9. FRONT-01 — инструкция для ONN9IX

### Результат

- существует `frontend/`;
- Next.js + TypeScript запускается;
- приложение открывается локально;
- задано место для Backend URL;
- нет отдельной БД;
- создан PR.

### 9.1 Начало

```bash
git fetch origin
git checkout main
git pull origin main
git checkout -b frontend/FRONT-01-init --track origin/frontend/FRONT-01-init
```

### 9.2 Создание

Создать Next.js TypeScript application в папке `frontend/`. Не создавать отдельный Git-репозиторий внутри `frontend/`.

Frontend не устанавливает SQLite/PostgreSQL ORM. Он не работает с БД напрямую.

### 9.3 Environment

`frontend/.env.example`:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

Локальное значение хранить в `.env.local`, который не коммитится.

### 9.4 Проверка

Frontend должен запускаться на `http://localhost:3000`.

На FRONT-01 не нужно делать Login, Dashboard и реальные запросы. Цель — чистый рабочий каркас.

### 9.5 Commit

```bash
git add .
git commit -m "FRONT-01: initialize Next.js frontend"
git push -u origin frontend/FRONT-01-init
```

Создать PR в `main`, указать `Closes #14`.

## 10. Когда впервые соединяем Frontend и Backend

После появления Backend auth endpoints и Frontend API client начинается реальная интеграция. Auth transport уже зафиксирован: server-side session в PostgreSQL + HttpOnly cookie `smart_garden_session`; Frontend использует credentials и не хранит raw token.

Целевая локальная схема:
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- API: `http://localhost:8000/api/v1`
- PostgreSQL: локальный Backend PostgreSQL

Frontend отправляет запрос Backend. Backend читает/изменяет PostgreSQL. Ответ возвращается Frontend.

## 11. Интеграционный checkpoint Этапа 1

Этап нельзя считать готовым, пока на одном компьютере не пройдёт сценарий:

1. запущен PostgreSQL;
2. запущен Backend;
3. запущен Frontend;
4. открыть Frontend;
5. ввести demo username + временный пароль;
6. Frontend вызывает Backend login;
7. Backend проверяет пользователя в PostgreSQL;
8. Backend сообщает `must_change_password=true`;
9. Frontend переводит на смену пароля;
10. новый пароль отправляется Backend;
11. Backend сохраняет новый hash в PostgreSQL;
12. старый временный пароль больше не работает;
13. `GET /auth/me` возвращает пользователя и организацию;
14. Frontend открывает Dashboard;
15. Logout завершает сессию.

Если хотя бы один пункт не работает — Этап 1 не завершён.

## 12. Что делать, если разработчик не понимает Issue

Не импровизировать. Порядок:
1. открыть Issue;
2. открыть соответствующий stage-документ;
3. открыть API contract;
4. проверить этот единый guide;
5. если ответ всё равно не найден — задать вопрос до написания кода.

Особенно нельзя самостоятельно менять:
- БД;
- стек;
- API URL;
- JSON contract;
- роли;
- auth flow;
- tenant model;
- password flow;
- поля персональных данных.

## 13. Definition of Done для каждой задачи

Issue закрывается только если:
- код запускается;
- вручную созданные нетривиальные source-файлы имеют полезный header comment/docstring по `docs/09-code-and-error-standards.md`;
- ошибки обрабатываются по общему стандарту, без raw stack trace клиенту;
- требования Issue выполнены;
- существующий функционал не сломан;
- нет секретов/реальных ПДн;
- нет второй БД;
- API соответствует контракту;
- сделан осмысленный commit;
- создан PR;
- PR проверен;
- изменения merged в `main`.

## 14. Следующий этап

После завершения BACK-01 и FRONT-01 оба разработчика обновляют `main` и только затем берут BACK-02 / FRONT-02. Все последующие задачи строятся на общей кодовой базе. Это предотвращает ситуацию, когда Backend и Frontend развиваются как несовместимые проекты.


## 15. Смена ролей и воспроизводимость окружения

Frontend/Backend не привязаны к конкретному человеку навсегда. Перед передачей работы другому разработчику проект обязан быть воспроизводим по Git.

Обязательно:
- локальная PostgreSQL поднимается через `docker-compose.yml`;
- `.env.example` содержит все названия переменных;
- реальные secrets не передаются в сообщениях;
- demo users создаются seed-скриптом;
- migrations и README находятся в Git;
- staging/production secrets в будущем хранятся централизованно, а не на компьютере разработчика.

Полная политика: `docs/08-team-access-and-environments.md`.

Критерий передачи: новый разработчик должен поднять соответствующую часть системы без вопроса «какой у тебя пароль/файл/настройка?».
