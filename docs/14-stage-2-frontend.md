# ТЗ Stage 2 — Frontend

**Проект:** Умный сад  
**Этап:** Stage 2 — Groups / Children / Guardians / PARENT account  
**Исполнитель Stage 2:** F1zname  
**Статус:** Ready for development после merge этого документа и API Contract  
**Источник решений:** `docs/12-stage-2-data-model-and-decisions.md`  
**Обязательно прочитать:** `docs/00-development-guide.md`, `docs/09-code-and-error-standards.md`, `docs/13-stage-2-backend.md`, Stage 2 API Contract.

---

# 0. Цель Frontend Stage 2

Сделать рабочий интерфейс для первого бизнес-сценария:

```text
DIRECTOR / ADMIN
→ создаёт группу
→ создаёт ребёнка
→ создаёт/выбирает представителя
→ связывает его с ребёнком
→ создаёт PARENT account
→ получает временные credentials один раз
```

Frontend не хранит собственные бизнес-данные и не использует mock после подключения API.

---

# 1. Что уже есть и сохраняется

Не переписывать без необходимости:
- Next.js App Router;
- React;
- TypeScript;
- общий `api` client;
- AuthProvider;
- AuthGate;
- AppShell;
- UI components;
- server-side session cookie;
- `credentials: "include"`;
- общий error mapping;
- loading/error patterns.

---

# 2. Новая структура routes

Создать:

```text
frontend/src/app/groups/page.tsx
frontend/src/app/groups/[id]/page.tsx

frontend/src/app/children/page.tsx
frontend/src/app/children/new/page.tsx
frontend/src/app/children/[id]/page.tsx

frontend/src/app/guardians/page.tsx
frontend/src/app/guardians/new/page.tsx
frontend/src/app/guardians/[id]/page.tsx

frontend/src/app/parent/page.tsx
```

Не создавать:
- attendance;
- employees;
- announcements;
- payments;
- parent child-view UI.

---

# 3. Sidebar

Текущий disabled menu обновить:

Активные в Stage 2:
- Главная
- Дети
- Группы
- Родители

Остаются disabled:
- Сотрудники
- Посещаемость
- Объявления
- Настройки

Меню DIRECTOR и ADMIN одинаковое для Stage 2.

PARENT не использует management AppShell.

---

# 4. PARENT routing

Обновить:
- `frontend/src/types/auth.ts`;
- `frontend/src/features/auth/auth-gate.tsx`;
- при необходимости AuthProvider.

Добавить:

```ts
PARENT
```

Логика после auth:

```text
must_change_password=true
→ /change-password

role DIRECTOR|ADMIN
→ /dashboard

role PARENT
→ /parent
```

PARENT никогда не должен попадать на:
- /dashboard management UI;
- /groups;
- /children;
- /guardians.

Даже если вручную введёт URL:
- Frontend redirect/403;
- Backend всё равно возвращает 403.

---

# 5. Parent placeholder

`/parent` — не полноценный кабинет родителя.

Показывает:
- «Умный сад»;
- username;
- organization;
- роль «Родитель»;
- текст: «Родительский кабинет пока недоступен в этой версии»;
- Logout.

Не показывать:
- детей;
- группы;
- других родителей;
- сотрудников;
- внутреннее меню сада.

---

# 6. API client

Текущий `frontend/src/lib/api/client.ts` поддерживает GET/POST.

Stage 2 добавить:

```ts
patch<T>()
```

DELETE не добавлять.

Сохранить:
- credentials include;
- no-store;
- safe error parsing;
- не показывать raw server error.

Расширить user-friendly mapping новыми Stage 2 codes.

---

# 7. Transport types

Создать:

```text
frontend/src/types/stage2.ts
```

Типы должны повторять API Contract без самовольного rename:
- Group;
- Child;
- Guardian;
- ChildGuardian;
- ParentAccountSummary;
- temporary credential response;
- list responses.

Не писать отдельный type, если он уже существует в auth.

---

# 8. Feature API modules

Создать:

```text
frontend/src/lib/api/groups.ts
frontend/src/lib/api/children.ts
frontend/src/lib/api/guardians.ts
```

Parent account calls могут находиться в `guardians.ts`, так как lifecycle привязан к Guardian.

Каждый module:
- только transport calls;
- без JSX;
- без localStorage;
- без hardcoded organization_id.

---

# 9. Groups — список

`/groups`

Показывает:
- заголовок «Группы»;
- кнопку «Создать группу»;
- active groups;
- переключатель «Активные / Архив»;
- loading;
- empty;
- error;
- retry.

Для каждой группы:
- name;
- status;
- переход в detail.

Никаких фиктивных counts, если Backend их не возвращает.

---

# 10. Groups — создание

Форма:
- name.

После успеха:
- redirect в `/groups/{id}` либо list;
- показать success feedback.

Ошибки:
- `GROUP_NAME_CONFLICT` → «Группа с таким названием уже существует»;
- `VALIDATION_ERROR` → field/general message.

Не отправлять organization_id.

---

# 11. Group detail

`/groups/[id]`

Показывает:
- name;
- status;
- edit action;
- список active children этой группы;
- archive/restore.

Archive:
- перед действием confirmation;
- если Backend → `GROUP_NOT_EMPTY`, показать понятное сообщение;
- не пытаться «обойти» это скрытой Frontend логикой.

Restore:
- если name conflict, показать server-derived safe message.

---

# 12. Children — список

`/children`

Показывает:
- «Дети»;
- «Добавить ребёнка»;
- список;
- filter by Group;
- active/archive filter;
- search by name;
- loading/error/empty.

В строке/карточке:
- ФИО;
- дата рождения;
- group name;
- status.

Не показывать скрытые поля, которых нет в contract.

---

# 13. Child create

`/children/new`

Поля:
- фамилия;
- имя;
- отчество optional;
- дата рождения;
- группа.

Group select:
- только active groups, полученные Backend;
- никаких hardcoded options.

Если active groups нет:
- объяснить, что сначала нужно создать группу;
- ссылка «Создать группу».

После create → `/children/{id}`.

---

# 14. Child detail

`/children/[id]`

Показывает:
- ФИО;
- birth_date;
- group;
- status;
- Guardian relations.

Actions:
- edit;
- change group;
- archive/restore;
- add existing Guardian;
- create new Guardian;
- update relation type;
- unlink/archive relation.

Не добавлять free-text notes.

---

# 15. Guardians — список

Route:
`/guardians`

В UI раздел называется:

```text
Родители
```

На странице можно использовать уточнение:

```text
Родители и законные представители
```

Показывает:
- ФИО;
- phone if present;
- email if present;
- PARENT account status;
- active/archive filter;
- name search.

Нельзя выводить temporary password из какого-либо GET.

---

# 16. Guardian create

`/guardians/new`

Поля:
- last_name;
- first_name;
- middle_name optional;
- phone optional;
- email optional.

Phone/email не required.

Не добавлять:
- address;
- passport;
- job;
- notes.

После create → detail.

---

# 17. Guardian detail

`/guardians/[id]`

Блоки:

## 17.1. Основные данные

- ФИО;
- phone;
- email;
- status;
- edit/archive/restore.

## 17.2. Дети

Показать linked children:
- ФИО;
- group;
- relation_type.

Actions:
- link existing Child;
- change relation type;
- unlink.

## 17.3. Учётная запись

Если account=null:
- «Создать учётную запись родителя».

Если account существует:
- username;
- status;
- must_change_password state;
- «Сбросить пароль»;
- block/unblock.

Никогда не показывать password из GET.

---

# 18. Relation type labels

Transport values:

```text
mother
father
legal_guardian
other
```

UI labels:

```text
Мать
Отец
Законный представитель
Другой представитель
```

Frontend не должен отправлять переведённый русский label вместо API value.

---

# 19. Temporary credentials UI

После:
- create PARENT account;
- reset password;

Backend возвращает:
- username;
- temporary_password.

Frontend показывает отдельную одноразовую карточку/modal:

```text
Логин: ...
Временный пароль: ...
Пароль показывается только сейчас.
Передайте его родителю безопасным способом.
```

Можно добавить copy buttons.

Строго запрещено:
- localStorage;
- sessionStorage;
- URL params;
- analytics event payload;
- console.log;
- повторное сохранение credentials в state дольше текущего экрана, чем нужно.

После закрытия/refresh получить temporary password повторно нельзя.

---

# 20. Archive UI

Вместо «Удалить» использовать:
- «Архивировать»;
- «Восстановить».

Перед archive — confirmation.

Архивные сущности должны визуально отличаться, но не использовать агрессивную стилизацию.

Не использовать hidden hard delete.

---

# 21. Forms

Требования:
- labels всегда видимы;
- required fields отмечены;
- optional поля явно помечены;
- submit disabled while request in progress;
- double submit предотвращён;
- server validation отображается безопасно;
- при server error введённые пользователем значения не теряются без причины.

---

# 22. Dates

API:
- `birth_date` — YYYY-MM-DD;
- datetime — UTC ISO8601.

Frontend:
- birth date показывать в понятном локальном формате;
- при submit отправлять YYYY-MM-DD;
- не делать timezone conversion для date-only birth_date.

---

# 23. Loading / empty / error

Каждая новая list/detail page должна иметь:

```text
loading
success
empty (если применимо)
safe error
retry
```

Не оставлять blank page.

---

# 24. 404 / 403

404:
- entity not found либо hidden foreign tenant;
- показать нейтральное «Запись не найдена».

403:
- «Действие недоступно».

Не писать:
- «Запись принадлежит другому саду»;
- «У вас нет доступа к саду X».

---

# 25. Personal data UX

Stage 2 UI не должен:
- показывать лишние ПДн;
- помещать ПДн в URL query, кроме UUID/filter;
- писать ФИО/телефоны/email в console;
- сохранять формы в browser storage;
- отправлять данные во внешнюю аналитику.

Dev/demo screenshots — только synthetic data.

---

# 26. Feature structure

Рекомендуемая структура:

```text
frontend/src/features/groups/
frontend/src/features/children/
frontend/src/features/guardians/
frontend/src/features/parent/
```

Пример:
- form components;
- list components;
- detail components;
- small role-aware helpers.

Не делать один `stage2.tsx` на тысячу строк.

---

# 27. Reusable UI

Можно добавить:

```text
frontend/src/components/ui/select.tsx
frontend/src/components/ui/confirm-dialog.tsx
frontend/src/components/ui/status-badge.tsx
```

Только если реально используются минимум в Stage 2.

Не подключать большую UI library без отдельного решения.

---

# 28. Responsive

Минимум проверить:
- desktop;
- tablet width;
- mobile width.

На mobile:
- формы не выходят за экран;
- temporary credential block читаем;
- sidebar/nav не ломает layout;
- actions доступны.

---

# 29. Accessibility baseline

- input связан с label;
- buttons — реальные button;
- disabled state;
- focus visible;
- errors доступны через text/role;
- modal/confirm, если создаётся, не должен быть div-only без keyboard support.

---

# 30. Tests

Расширить Playwright:

```text
frontend/tests/stage2.spec.ts
```

Минимум browser scenarios:

## 30.1. Management happy path

```text
login DIRECTOR
→ group create
→ child create
→ guardian create
→ link guardian
→ create PARENT account
→ temporary credentials visible
```

## 30.2. Archive rule

```text
group with child
→ archive
→ GROUP_NOT_EMPTY message
```

## 30.3. Parent flow

```text
PARENT login temp password
→ change password
→ /parent
→ management links absent
→ direct /children attempt blocked/redirected
```

## 30.4. Logout

Оба типа роли корректно logout.

---

# 31. API error mapping

Добавить понятные user messages минимум для:

```text
GROUP_NAME_CONFLICT
GROUP_NOT_EMPTY
GROUP_ARCHIVED
INVALID_BIRTH_DATE
CHILD_ARCHIVED
GUARDIAN_ARCHIVED
GUARDIAN_HAS_ACTIVE_CHILDREN
RELATION_ALREADY_EXISTS
PARENT_ACCOUNT_ALREADY_EXISTS
PARENT_ACCOUNT_NOT_FOUND
PARENT_ACCOUNT_BLOCKED
```

Если unknown:
- generic safe fallback;
- raw message Backend не показывать.

---

# 32. Что не делать

Не реализовывать:
- payment UI;
- attendance;
- teacher;
- documents;
- photo upload;
- chats;
- email/SMS sending;
- parent child data;
- Excel import;
- analytics SDK;
- data export;
- delete buttons.

---

# 33. Проверки разработчика

В `frontend/`:

```bash
npm ci
npm run lint
npm run build
npx playwright test
```

Также:
- browser console без errors;
- Network не содержит organization_id в create forms;
- temporary password не появляется в storage;
- role PARENT не видит management shell.

---

# 34. Definition of Done Frontend Stage 2

- [ ] PARENT role поддержан;
- [ ] role-based redirect работает;
- [ ] sidebar Stage 2 активирован;
- [ ] Groups list/create/detail/edit/archive/restore;
- [ ] Children list/create/detail/edit/archive/restore;
- [ ] Guardian list/create/detail/edit/archive/restore;
- [ ] Child↔Guardian UI;
- [ ] PARENT account create/reset/block/unblock UI;
- [ ] temporary credentials one-time UI;
- [ ] Parent placeholder безопасен;
- [ ] no mock business data;
- [ ] loading/error/empty states;
- [ ] responsive;
- [ ] lint green;
- [ ] build green;
- [ ] Playwright Stage 1 + Stage 2 green.
