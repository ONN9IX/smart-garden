# Stage 2 — модель данных и принятые решения

**Проект:** Умный сад  
**Этап:** Stage 2 — Groups / Children / Guardians / PARENT account  
**Статус:** design freeze candidate — код Stage 2 не начинать до согласования и merge этого документа  
**Issue:** #34  
**Ветка:** `docs/STAGE2-design`

Этот документ фиксирует единую модель данных и спорные решения Stage 2 до подготовки отдельных Backend/Frontend ТЗ и обновления API Contract.

При конфликте с ранним roadmap этот документ имеет приоритет после merge в `main`.

---

# 1. Цель Stage 2

Stage 2 должен дать первый полноценный рабочий бизнес-сценарий:

```text
DIRECTOR / ADMIN
        ↓
создаёт группу
        ↓
добавляет ребёнка
        ↓
добавляет законного представителя
        ↓
связывает представителя с ребёнком
        ↓
при необходимости создаёт PARENT account
        ↓
получает временные credentials один раз
```

Stage 2 не должен превращаться в полноценный кабинет родителя, модуль посещаемости или CRM.

---

# 2. Обязательные общие правила

Для всего Stage 2 сохраняются правила Stage 1:

1. Frontend → Backend `/api/v1` → PostgreSQL.
2. Единственная application DB — PostgreSQL.
3. Все public entity IDs — UUID strings.
4. Backend является источником истины по RBAC и tenant isolation.
5. Frontend не определяет `organization_id` для доступа к данным.
6. Все данные выбираются в контексте организации текущей server-side session.
7. API JSON — `snake_case`.
8. Клиентская validation error — HTTP 400 + `VALIDATION_ERROR`.
9. 404 используется также для сокрытия чужой tenant entity.
10. Никаких реальных ПДн в dev/test/seed.
11. Password, password hash, raw session token не логируются и не возвращаются.
12. Hard delete бизнес-сущностей в public API Stage 2 отсутствует.

---

# 3. Модель связей

```text
Organization
  │
  ├── 1 ─── * Group
  │            │
  │            └── 1 ─── * Child
  │
  ├── 1 ─── * Guardian
  │            │
  │            ├── 0..1 User(role=PARENT)
  │            │
  │            └── * ─── * Child
  │                    через ChildGuardian
  │
  └── 1 ─── * User
```

Ключевое решение:

- один Child может иметь несколько Guardian;
- один Guardian может быть связан с несколькими Child;
- связь реализуется отдельной сущностью `ChildGuardian`;
- один Guardian имеет максимум один PARENT account;
- один PARENT account принадлежит ровно одному Guardian;
- PARENT account не хранит отдельную копию ФИО/телефона/email.

---

# 4. Entity: Group

## 4.1. Назначение

Группа детского сада, к которой относится ребёнок.

## 4.2. Поля

```text
id                UUID PK
organization_id   UUID FK -> Organization.id
name              varchar(100)
status            active | archived
archived_at       timestamptz nullable
created_at        timestamptz
updated_at        timestamptz
```

## 4.3. Правила

- `name` после trim: 1–100 символов.
- В одной организации одновременно не может быть двух **активных** групп с одинаковым именем без учёта регистра.
- В разных организациях одинаковые названия допустимы.
- Группа создаётся только в организации текущего пользователя.
- `organization_id` из request body не принимается.
- Группу нельзя архивировать, пока в ней есть активные дети.
- Ошибка при попытке архивировать непустую группу: HTTP 409 `GROUP_NOT_EMPTY`.
- Восстановление группы допускается, если не возникает конфликт активного имени.

## 4.4. Почему не добавляем сейчас

Не добавляем:
- возрастной диапазон;
- учебный год;
- корпус;
- помещение;
- воспитателя;
- вместимость;
- расписание;
- произвольные notes.

Эти поля не нужны бизнес-сценарию Stage 2.

---

# 5. Entity: Child

## 5.1. Назначение

Минимальная карточка ребёнка для учёта в группе и связи с законными представителями.

## 5.2. Поля

```text
id                UUID PK
organization_id   UUID FK -> Organization.id
group_id          UUID FK -> Group.id
first_name        varchar(100)
last_name         varchar(100)
middle_name       varchar(100) nullable
birth_date        date
status            active | archived
archived_at       timestamptz nullable
created_at        timestamptz
updated_at        timestamptz
```

## 5.3. Правила

- `first_name`, `last_name`: обязательные, trim, 1–100 символов.
- `middle_name`: optional; пустая строка нормализуется в `null`.
- `birth_date`: обязательна и не может быть в будущем.
- Возрастные ограничения программно в Stage 2 не задаются.
- `group_id` обязателен при создании активного ребёнка.
- Group должна:
  - существовать;
  - принадлежать текущей организации;
  - иметь `status=active`.
- Перевод ребёнка в другую активную группу своей организации разрешён.
- Два ребёнка могут иметь одинаковые ФИО и дату рождения — уникальность по этим полям запрещена, в том числе из-за возможных близнецов.
- Архивация Child не удаляет карточку и историю связей.
- Восстановить Child можно только в активную Group.
- Если прежняя Group архивирована, сначала нужно восстановить группу либо выбрать другую активную группу.

## 5.4. Сознательно не собираем

Stage 2 не содержит:
- адрес;
- гражданство;
- СНИЛС;
- номер свидетельства о рождении;
- паспортные данные;
- медицинские сведения;
- диагнозы;
- аллергии;
- лекарства;
- инвалидность;
- фотографии;
- биометрию;
- свободное текстовое поле «примечание».

Свободный comment/notes также не добавляется, чтобы сотрудники случайно не начали хранить в нём чувствительные или избыточные сведения.

---

# 6. Entity: Guardian

## 6.1. Термин

В коде используется `Guardian` как техническое имя сущности.

В интерфейсе допустимое пользовательское название:

```text
Родители / законные представители
```

Сущность не предполагает, что каждый Guardian обязательно является биологическим родителем.

## 6.2. Поля

```text
id                UUID PK
organization_id   UUID FK -> Organization.id
user_id           UUID FK -> User.id nullable UNIQUE
first_name        varchar(100)
last_name         varchar(100)
middle_name       varchar(100) nullable
phone             varchar(32) nullable
email             varchar(254) nullable
status            active | archived
archived_at       timestamptz nullable
created_at        timestamptz
updated_at        timestamptz
```

## 6.3. Правила

- ФИО валидируется аналогично Child.
- `phone` optional.
- `email` optional.
- Нельзя требовать телефон или email только ради создания карточки Guardian.
- `email`, если указан, хранится нормализованным по регистру.
- Телефон/email не являются username и не используются как обязательный login Stage 2.
- Уникальность Guardian по ФИО/phone/email не вводится: совпадения возможны.
- `user_id` устанавливает Backend только при создании PARENT account.
- Один `User(role=PARENT)` нельзя привязать к нескольким Guardian.
- Guardian и его User обязаны принадлежать одной организации.
- Guardian нельзя архивировать, если у него есть активные связи с активными детьми.
- В таком случае: HTTP 409 `GUARDIAN_HAS_ACTIVE_CHILDREN`.
- Перед архивированием Guardian пользователь должен явно убрать соответствующие связи.
- Архивация Guardian не выполняет скрытый cascade-delete.

---

# 7. Entity: ChildGuardian

## 7.1. Назначение

Связь many-to-many между Child и Guardian.

## 7.2. Поля

```text
id                UUID PK
organization_id   UUID FK -> Organization.id
child_id          UUID FK -> Child.id
guardian_id       UUID FK -> Guardian.id
relation_type     mother | father | legal_guardian | other
status            active | archived
archived_at       timestamptz nullable
created_at        timestamptz
updated_at        timestamptz
```

## 7.3. Почему relation_type находится здесь

Тип отношения относится к конкретной паре Child ↔ Guardian, а не к Guardian вообще.

Это исключает ошибочную модель, где одна общая характеристика Guardian автоматически применяется ко всем детям.

## 7.4. Правила

- Child и Guardian должны принадлежать одной организации текущего пользователя.
- Нельзя связать сущности из разных организаций.
- Создать вторую активную связь той же пары нельзя.
- Повторное добавление ранее архивированной пары должно восстанавливать/реактивировать существующую связь, а не плодить дубликаты.
- Изменение `relation_type` допустимо без пересоздания связи.
- У ребёнка в Stage 2 может временно быть 0 Guardian.
- У Guardian может быть 0 или несколько Child.
- Отвязка выполняется архивированием связи, а не physical DELETE.

---

# 8. PARENT account

## 8.1. Основное решение

PARENT account — существующая сущность `User` с:

```text
role = PARENT
organization_id = Guardian.organization_id
guardian.user_id = User.id
```

Отдельную таблицу `ParentUser` не создаём.

## 8.2. Создание

DIRECTOR или ADMIN может создать PARENT account только для активного Guardian своей организации.

Backend:

1. Проверяет tenant.
2. Проверяет, что Guardian active.
3. Проверяет отсутствие `guardian.user_id`.
4. Генерирует уникальный username.
5. Генерирует криптографически стойкий temporary password.
6. Хранит только password hash.
7. Создаёт User:
   - `role=PARENT`;
   - `status=active`;
   - `must_change_password=true`.
8. Привязывает User к Guardian.
9. Возвращает временный пароль **ровно в ответе операции создания**.

Temporary password:
- не пишется в БД в открытом виде;
- не пишется в logs;
- не доступен повторным GET;
- Frontend показывает его один раз с явным предупреждением.

## 8.3. Username

Username Stage 2:
- генерируется Backend;
- не строится из ФИО, телефона или email;
- содержит нейтральный случайный suffix;
- проверяется на глобальную уникальность User.username.

Пример формата:

```text
parent-k4m8r2q9
```

Формат не является частью персональных данных Guardian и не должен позволять угадывать имя или телефон.

## 8.4. Login PARENT

Backend auth расширяется на роль `PARENT`.

PARENT в Stage 2 может:
- login;
- пройти обязательную смену временного пароля;
- вызвать `GET /auth/me`;
- logout.

PARENT **не получает** в Stage 2 доступ к management endpoints Groups/Children/Guardians.

Полноценные данные детей для PARENT будут спроектированы отдельно в будущем Parent UI.

## 8.5. Frontend для PARENT

Полный родительский кабинет не входит в Stage 2.

Чтобы PARENT не попал в интерфейс DIRECTOR/ADMIN, Frontend должен иметь безопасный технический экран после входа:

```text
«Родительский кабинет пока недоступен в этой версии»
```

На нём доступны только:
- информация о текущем аккаунте;
- logout.

Никакие списки детей/родителей/сотрудников через этот экран не показываются.

## 8.6. Reset temporary password

DIRECTOR/ADMIN может сбросить пароль только PARENT account своей организации.

После reset:
- старый password hash заменяется;
- `must_change_password=true`;
- все sessions этого PARENT revoked;
- новый temporary password показывается один раз;
- старый пароль более не работает.

## 8.7. Block / unblock

Stage 2 включает блокировку и разблокировку PARENT account.

- DIRECTOR/ADMIN может блокировать только PARENT пользователя своей организации через Guardian workflow.
- Stage 2 не даёт ADMIN возможности блокировать/изменять DIRECTOR.
- Blocked PARENT не может войти даже при наличии старой session.

---

# 9. Archive / restore policy

## 9.1. Общий принцип

Для Group, Child, Guardian и ChildGuardian:

```text
active → archived
archived → active
```

Public hard delete отсутствует.

## 9.2. Причина

Это защищает от случайного уничтожения бизнес-данных и оставляет основу для будущего Audit Log.

## 9.3. API следствие

Не использовать:

```http
DELETE /groups/{id}
DELETE /children/{id}
DELETE /guardians/{id}
```

Вместо этого проектируются явные команды:

```text
archive
restore
```

## 9.4. Default list behavior

По умолчанию list endpoints показывают только `status=active`.

Для просмотра архива Frontend явно запрашивает `status=archived` или `status=all`.

---

# 10. Tenant isolation

Это security requirement, а не UI feature.

Для каждой Group/Child/Guardian/ChildGuardian/PARENT operation Backend обязан:

1. определить User по server-side session;
2. определить `organization_id` этого User;
3. искать business entity только внутри этого tenant;
4. не доверять `organization_id`, присланному клиентом;
5. возвращать 404 для сущности другого tenant, чтобы не подтверждать её существование.

Особое правило для связей:

```text
Child.organization_id
==
Guardian.organization_id
==
CurrentUser.organization_id
```

Любое нарушение — операция запрещена.

Tenant isolation должна проверяться automated tests минимум на двух synthetic organizations.

---

# 11. RBAC Stage 2

| Действие | DIRECTOR | ADMIN | PARENT |
|---|---:|---:|---:|
| Просматривать Groups | Да | Да | Нет |
| Создавать/изменять Groups | Да | Да | Нет |
| Archive/restore Groups | Да | Да | Нет |
| Просматривать Children | Да | Да | Нет |
| Создавать/изменять Children | Да | Да | Нет |
| Archive/restore Children | Да | Да | Нет |
| Просматривать Guardians | Да | Да | Нет |
| Создавать/изменять Guardians | Да | Да | Нет |
| Управлять Child↔Guardian | Да | Да | Нет |
| Создать PARENT account | Да | Да | Нет |
| Reset PARENT password | Да | Да | Нет |
| Block/unblock PARENT | Да | Да | Нет |
| Login / auth/me / logout | Да | Да | Да |
| Management UI | Да | Да | Нет |

Frontend использует эту матрицу для UX, но Backend проверяет каждое право самостоятельно.

---

# 12. Минимизация персональных данных

На Stage 2 появляются реальные категории ПДн детей и их представителей, поэтому состав полей специально ограничен.

## 12.1. Child

Нужны только:
- ФИО;
- дата рождения;
- принадлежность к группе.

## 12.2. Guardian

Нужны только:
- ФИО;
- optional телефон;
- optional email;
- связи с детьми.

## 12.3. Запрещено добавлять «про запас»

Без отдельного product/legal решения не добавляются:
- документы;
- адрес;
- фото;
- медицина;
- биометрия;
- платежные данные;
- место работы;
- паспорт;
- СНИЛС;
- произвольные заметки.

## 12.4. Dev/Test

В seed/tests/screenshots/issues:
- только synthetic names/data;
- не копировать production DB;
- не вставлять реальные ФИО/телефоны детей и родителей в GitHub Issues или logs.

---

# 13. Технический baseline по 152-ФЗ для Stage 2

Это технический baseline, **не юридическое заключение**.

На дату проектирования сверена действующая публикация 152-ФЗ в редакции от 26.07.2026.

Для архитектуры Stage 2 учитываем:

1. Статья 5: данные должны соответствовать конкретным целям обработки и не быть избыточными.
2. Статья 18 ч. 5: при сборе ПДн граждан РФ действует требование по использованию баз данных на территории РФ для перечисленных законом операций, с предусмотренными законом исключениями.
3. Статья 19: требуются правовые, организационные и технические меры защиты от неправомерного/случайного доступа и иных неправомерных действий.

Практические следствия для разработки:
- data minimization встроена в schema;
- production DB/location не выбирается «как удобнее разработчику»;
- до pilot нельзя подключать внешние SaaS, куда могут уходить ПДн, без проверки data flow;
- tenant isolation и access rules тестируются на Backend;
- чувствительное содержимое не попадает в application logs;
- для реального pilot до загрузки ПДн требуется отдельная юридико-техническая проверка оператора, оснований обработки, договоров/поручения, документации и инфраструктуры.

---

# 14. Validation и бизнес-ошибки

Используется общий error contract проекта.

Минимальные новые error codes:

```text
GROUP_NAME_CONFLICT
GROUP_NOT_EMPTY
GROUP_ARCHIVED

CHILD_ARCHIVED
INVALID_BIRTH_DATE

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

Tenant mismatch не должен иметь отдельный публичный error, раскрывающий наличие чужой сущности. Для клиента — 404.

---

# 15. Transaction rules

Операции, изменяющие несколько сущностей, атомарны.

Обязательно одна DB transaction для:
- создания PARENT User + привязки `guardian.user_id`;
- reset PARENT password + revoke sessions;
- реактивации ChildGuardian;
- archive/restore там, где меняются связанные поля.

При исключении transaction откатывается полностью.

---

# 16. Index / constraint baseline

Backend migration Stage 2 должна предусмотреть минимум:

- FK на Organization;
- FK Child → Group;
- FK Guardian → User nullable;
- FK ChildGuardian → Child;
- FK ChildGuardian → Guardian;
- unique Guardian.user_id when not null;
- unique ChildGuardian pair `(child_id, guardian_id)`;
- индекс Child `(organization_id, status, group_id)`;
- индекс Guardian `(organization_id, status)`;
- индекс Group `(organization_id, status)`;
- constraint/check для допустимых status/relation_type либо эквивалентный DB enum/validated domain;
- механизм уникальности активного имени Group в пределах tenant.

Конкретную реализацию enum/check выбирает Backend ТЗ, но public API values должны остаться зафиксированными.

---

# 17. Бизнес-сценарии, которые обязаны пройти

## Scenario A — базовый happy path

```text
DIRECTOR
→ создаёт Group «Ромашка»
→ создаёт Child
→ создаёт Guardian
→ связывает Guardian с Child как mother
→ создаёт PARENT account
→ получает username + temp password один раз
```

## Scenario B — несколько детей одного Guardian

```text
Guardian
→ Child A
→ Child B
→ один PARENT account
```

Нельзя создавать второй PARENT account для того же Guardian.

## Scenario C — два Guardian одного Child

```text
Child
→ Guardian 1 mother
→ Guardian 2 father
```

## Scenario D — tenant isolation

User сада A не может:
- получить Child сада B;
- изменить Guardian сада B;
- использовать UUID Group сада B при создании Child;
- связать Child A с Guardian B.

Во всех случаях Backend fail closed.

## Scenario E — archive

- Group с активными детьми архивировать нельзя.
- Guardian с активными связями архивировать нельзя.
- Child можно архивировать без physical delete.
- Archived entity по default не видна в active list.
- Restore возвращает сущность только после проверки конфликтов.

## Scenario F — PARENT security

- temporary password показывается только при create/reset;
- после обязательной смены старый temporary password не работает;
- reset отзывает старые sessions;
- blocked PARENT не входит;
- PARENT не получает management API.

---

# 18. Что точно НЕ входит в Stage 2

Не реализовывать без отдельного изменения scope:

- Attendance;
- Employees/Teacher;
- Teacher UI;
- полноценный Parent UI;
- просмотр ребёнка родителем;
- announcements;
- payments;
- photos;
- chats;
- medical records;
- documents;
- СКУД;
- entrance tablet;
- trusted pickup persons;
- AI;
- analytics;
- imports from Excel;
- email/SMS sending;
- password recovery через email/SMS;
- external integrations.

---

# 19. Следующий шаг после согласования этого документа

После merge design freeze последовательно создаются:

1. `docs/13-stage-2-backend.md` — исполняемое Backend ТЗ.
2. `docs/14-stage-2-frontend.md` — исполняемое Frontend ТЗ.
3. `docs/15-api-contract-stage-2.md` либо versioned update API contract.
4. Stage 2 GitHub Issues с зависимостями.
5. Integration Issue с Browser → Frontend → Backend → PostgreSQL сценариями.
6. Только затем — feature branches и код.

---

# 20. Design freeze rule

После начала Stage 2 разработки нельзя молча менять:
- поля entity;
- API values;
- role permissions;
- archive semantics;
- PARENT lifecycle;
- tenant behavior.

Любое изменение:
1. отдельная Issue;
2. обновление design/API docs;
3. синхронная проверка Frontend и Backend;
4. только потом код.
