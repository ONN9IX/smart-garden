# ТЗ Stage 3 — Backend

**Источник решений:** `docs/17-stage-3-data-model-and-decisions.md`. **Контракт:** `docs/20-api-contract-stage-3.md`. Применяются также `docs/00-development-guide.md`, `docs/05-personal-data-baseline.md`, `docs/09-code-and-error-standards.md`.

## 1. Результат

DIRECTOR/ADMIN ведут карточки Employee и ручную посещаемость в пределах своего сада. Только DIRECTOR управляет связанными ADMIN аккаунтами. PARENT не получает новый доступ. Не активировать TEACHER, не вводить новый способ авторизации или хранилище.

## 2. База и модели

- `0007_employees`: таблица Employee по документу 17; FK на Organization и nullable unique FK на User; индекс `(organization_id, status)`; checks статуса и непустых имён/должности после trim. Один User не может быть привязан к двум Employee. Downgrade удаляет только новую таблицу.
- `0008_attendance`: поля по документу 17; FK на Organization, Child, Group, created_by/updated_by User; unique `(child_id, date)`; checks status и комбинаций времени; индексы по tenant/date/group и tenant/date/status. Downgrade удаляет таблицу. Проверять tenant consistency на сервисном уровне; SQL checks не заменяют эти проверки.
- Добавить модели в metadata для Alembic. Не менять записи или ограничения Stage 2 ради новой схемы. Время — SQL `TIME` без часового пояса, дата — SQL `DATE`; не сохранять произвольный text comment.

## 3. Employee service

Сервис содержит все запросы с `organization_id == actor.organization_id`, create/patch/archive/restore, поиск по ФИО, создание и управление ADMIN account. Тонкие HTTP handlers только разрешают роли и вызывают сервис. Статус по умолчанию `active`; архивный Employee виден через `status=archived|all`.

Create account: только DIRECTOR, активная карточка без `user_id`; случайный `staff-` username, не производный от ФИО; Argon2id, временный пароль, `must_change_password=true`; Employee+User связываются атомарно. При глобальной коллизии username — retry с savepoint. Reset: новый hash + `must_change_password` + отзыв всех сессий в одной транзакции. Block: статус User blocked + отзыв сессий в одной транзакции. Unblock: только активный Employee, без выдачи сессии. Archive Employee со связанным User — только DIRECTOR: блокировка User и отзыв сессий атомарно; ADMIN может архивировать лишь карточку без аккаунта. Restore Employee сохраняет User blocked. Ошибки 404/409 по контракту. Никакой выдачи второго аккаунта или изменения существующей роли.

## 4. Attendance service

`GET /attendance` получает date, optional group/status/child filters. Список дня включает активных детей текущих активных групп и архивных детей, у которых уже есть Attendance на выбранную дату. Для активного ребёнка без строки Attendance возвращать вычисленный `unknown`, `record_id=null`, без записи в БД. Для сохранённой строки использовать `group_id` снимка, а не текущую группу ребёнка. Хранить дату и времена строго как date/time, не как UTC datetime. Фильтр status применяется после вычисления unknown. Сортировка group/name/UUID стабильна.

`POST /attendance` атомарно создаёт или обновляет пару `(child_id,date)`; group_id фиксируется при первой записи, created_by не меняется, updated_by и updated_at меняются. При гонке unique constraint повторно прочитать/обновить запись внутри корректной транзакции, не возвращать 500. Можно обновить `present` на `unknown` для исправления, строку не удалять. Для archived Child запись запрещена; для active Child с archived Group новая запись также запрещена. `GET /attendance/{id}` и `PATCH /attendance/{id}` доступны лишь в своём tenant; PATCH меняет status/times, но не child/date/group/created_by. Любой запрос с чужим UUID скрывается 404.

## 5. Auth, роли, ошибки

`require_role("DIRECTOR", "ADMIN")` на чтение/изменение Employee и Attendance; account endpoints `require_role("DIRECTOR")`. `organization_id`, `created_by`, `updated_by`, `user_id`, `password_hash` запрещены в create/patch body. Общий безопасный error JSON, validation HTTP 400, tenant 404, conflict 409. Все новые маршруты/response schemas и error responses документированы в OpenAPI. Временный пароль только в create/reset response. Никогда не логировать тело формы, ФИО, дату/статус конкретного ребёнка, password/hash/token или query с именем.

## 6. Seed и проверки

Seed создаёт только синтетического Employee без доступа и несколько синтетических ручных отметок на фиксированную прошедшую дату, идемпотентно; не менять пароли уже существующих аккаунтов. Даты для браузерного E2E генерировать в тесте, не использовать реальные данные.

PostgreSQL pytest минимум: migration round trip; duplicate Employee.user_id; employee account lifecycle и отзыв сессий; ADMIN не может create/reset/block ADMIN account; PARENT denied; два сада и чужие UUID; attendance unique/upsert, unknown, дата будущего, проверки времени, archived child/group, сохранение снимка группы после перевода; rollback при конфликте. Существующие Stage 1/2 тесты зелёные. CI: Ruff, pytest, Alembic downgrade/upgrade, Frontend build, browser E2E, Docker preview, required gates.

## 7. Персональные данные — обязательный блок

Только ФИО/должность Employee и минимальные поля ручной отметки. Никакого comment, диагноза, причины отсутствия, документов, телефона, email и фотографий. Доступ только своего сада и по роли; PARENT не получает список сотрудников/посещаемость. Технические access logs не должны записывать query-параметры с ПДн. Dev/test/seed — только синтетические данные. Сроки хранения, основания обработки и инфраструктура для реального пилота требуют отдельной правовой и технической проверки по 152-ФЗ.

## Definition of Done

- Миграции и модели соответствуют документу 17; upgrade/downgrade зелёные.
- Employee CRUD/archive/restore и ADMIN account lifecycle работают без повышения прав.
- Attendance сохраняет одну запись на ребёнка/дату, неизвестные показываются, снимок группы сохраняется.
- Two-tenant и PARENT/RBAC suite зелёные, no plaintext in GET/logs/storage.
- OpenAPI соответствует документу 20; Frontend проходит полный сценарий без mock.
