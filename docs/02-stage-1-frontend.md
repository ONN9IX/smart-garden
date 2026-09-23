# ТЗ Этап 1 — Frontend / UX

**Проект:** Умный сад  
**Версия:** MVP 0.1  
**Исполнитель Stage 1:** ONN9IX (роль может смениться на следующем этапе)  
**Статус:** Ready for development  
**Перед кодом:** прочитать `docs/00-development-guide.md`, `docs/03-api-contract-v0.1.md`, `docs/08-team-access-and-environments.md`, `docs/09-code-and-error-standards.md`.

---

# 1. Цель этапа

Создать стабильный web-каркас приложения и полностью реализовать первый пользовательский сценарий:

```text
Открыть систему
→ увидеть Login
→ ввести username/password
→ если пароль временный — обязательно изменить его
→ получить текущего пользователя и роль
→ попасть в интерфейс своего сада
→ выйти из системы
```

На Этапе 1 бизнес-модули «Дети», «Группы» и т. д. отображаются только как будущие разделы либо неактивные пункты меню. Их функциональность пока не реализуется.

---

# 2. Рекомендуемый стек

- Next.js
- React
- TypeScript
- npm + committed `package-lock.json`
- ESLint

Допускается согласованная UI-библиотека.

Основное требование: не создавать сложную дизайн-систему раньше продукта.

---

# 3. Структура проекта

Ориентир:

```text
frontend/
├── src/
│   ├── app/
│   │   ├── login/
│   │   ├── change-password/
│   │   └── dashboard/
│   ├── components/
│   │   ├── ui/
│   │   └── layout/
│   ├── features/
│   │   └── auth/
│   ├── lib/
│   │   ├── api/
│   │   └── auth/
│   └── types/
├── public/
├── .env.example
└── README.md
```

---

# 4. Environment

`.env.example`:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

Не размещать API secrets во frontend environment.

Переменные с `NEXT_PUBLIC_` считаются доступными клиенту.

---

# 5. Маршруты Этапа 1

```text
/login
/change-password
/dashboard
```

Дополнительно:

```text
/403
/404
```

---

# 6. Login

Страница `/login`.

Поля:

```text
Логин
Пароль
```

Кнопка:

```text
Войти
```

Email не является обязательным и не используется для входа.

## UX

- autofocus на логин;
- пароль скрыт по умолчанию;
- возможность показать/скрыть пароль;
- кнопка блокируется во время запроса;
- двойная отправка формы предотвращается;
- Enter отправляет форму;
- ошибки выводятся понятным текстом.

---

# 7. Состояния Login

### Loading

```text
Вход...
```

### Неверные credentials

```text
Неверный логин или пароль
```

Не показывать пользователю, существует ли такой username.

### Blocked

```text
Доступ к аккаунту заблокирован. Обратитесь к администратору сада.
```

### Server error

```text
Не удалось выполнить вход. Попробуйте ещё раз.
```

Не показывать JSON, stack trace, status body сервера.

---

# 8. Временный пароль

Если Backend после входа сообщает:

```text
must_change_password = true
```

Frontend обязан направить пользователя на:

```text
/change-password
```

Нельзя позволить перейти в `/dashboard` до успешной смены пароля.

---

# 9. Change Password

Поля:

```text
Новый пароль
Повторите новый пароль
```

Frontend проверяет:

- поля заполнены;
- пароли совпадают;
- минимум 10 символов.

Backend остаётся конечным источником валидации.

После успешной обязательной смены:
- Backend отзывает старую временную session;
- Backend устанавливает новую HttpOnly session cookie;
- Frontend обновляет auth context через `/auth/me`;
- пользователь переходит в `/dashboard`.

Если `must_change_password=false`, этот Stage 1 endpoint не используется как обычная смена постоянного пароля.

---

# 10. Auth state

После загрузки защищённой части приложения Frontend обращается:

```http
GET /api/v1/auth/me
```

Сохраняются в application state только необходимые данные:

```text
user_id
username
role
organization_id
organization_name
must_change_password
```

Не хранить пароль.

---

# 11. Хранение auth credentials

Stage 1 использует **server-side session + HttpOnly cookie `smart_garden_session`**.

Frontend:
- не сохраняет token в `localStorage` или `sessionStorage`;
- не получает raw session token в JSON;
- не имеет JavaScript-доступа к session cookie;
- во всех auth requests использует credentials/cookies через единый API client;
- не реализует собственную альтернативную auth/session схему.

Источник истины: `docs/03-api-contract-v0.1.md`.

---

# 12. Protected routes

Правила:

### Неавторизованный пользователь

`/dashboard` → redirect `/login`

### Авторизован + must_change_password

`/dashboard` → redirect `/change-password`

### Авторизован + password changed

может открыть `/dashboard`.

### Авторизован на `/login`

перенаправить в соответствующий рабочий экран.

---

# 13. Основной Layout

После входа:

```text
┌────────────────────────────────────────────┐
│ Умный сад       Детский сад «Солнышко»   │
├──────────────┬─────────────────────────────┤
│ Главная      │                             │
│ Дети         │          Content            │
│ Группы       │                             │
│ Родители     │                             │
│ Сотрудники   │                             │
│ Посещаемость │                             │
│ Объявления   │                             │
│ Настройки    │                             │
└──────────────┴─────────────────────────────┘
```

На Этапе 1 реализована только «Главная» как технический экран.

Остальные пункты могут быть disabled либо вести на экран:

```text
Раздел будет реализован на следующем этапе
```

---

# 14. Верхняя панель

Показывает:

- название сада;
- username или ФИО, если доступно;
- роль;
- кнопку выхода.

Пример:

```text
Детский сад «Солнышко»
director-demo
Директор
Выйти
```

---

# 15. Dashboard Этапа 1

Это пока не бизнес-dashboard.

Показывает только подтверждение корректного auth context:

```text
Добро пожаловать

Детский сад:
Детский сад «Солнышко»

Пользователь:
director-demo

Роль:
Директор
```

Статистика детей будет добавлена позже.

---

# 16. Role-aware UI

Роль приходит от Backend.

В коде должны существовать единые role constants:

```text
DIRECTOR
ADMIN
```

Не использовать строки `"director"` в десятках компонентов вручную.

Подготовить механизм, позволяющий позже добавить:

```text
PARENT
TEACHER
SUPER_ADMIN
```

---

# 17. API Client

Создать единый API client.

Требования:

- base URL из environment;
- `credentials: "include"` для запросов, где нужна session cookie;
- единая обработка network errors;
- автоматическая работа с cookie/session;
- единый разбор backend error format;
- не делать raw fetch во всех компонентах.

---

# 18. Error mapping

Backend:

```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Неверный логин или пароль",
    "field": null
  }
}
```

Frontend должен иметь единое отображение ошибок.

Не дублировать обработку кодов на каждой странице.

---

# 19. UI-компоненты Этапа 1

Минимально:

```text
Button
Input
PasswordInput
FormField
Alert
Toast
Spinner / Loading
AppShell
Sidebar
Header
```

Не создавать компоненты для таблиц детей, календарей и прочего до соответствующего этапа.

---

# 20. Responsive

Основной MVP — desktop и планшет.

Минимально проверить:

- 1366px desktop;
- 1024px tablet;
- 768px narrow tablet.

Телефон должен оставаться функциональным, но полноценный mobile-first интерфейс родителей сейчас не требуется.

---

# 21. Accessibility baseline

- label связан с input;
- tab navigation работает;
- кнопки имеют понятные names;
- Enter работает в login;
- focus state не удалять;
- сообщения ошибок доступны рядом с формой.

---

# 22. Персональные данные

На Этапе 1:

- не выводить password в console;
- не выводить auth response целиком в console;
- не использовать реальные данные сотрудников;
- не отправлять username в стороннюю аналитику;
- не помещать ПДн в URL query;
- не подключать сторонний session replay без отдельного согласования.

---

# 23. Mock API

Frontend может начать раньше готового Backend.

Создать mock responses строго в формате общего API Contract.

Пример:

```json
{
  "user": {
    "id": "demo-user-1",
    "username": "director-demo",
    "role": "DIRECTOR",
    "status": "active",
    "must_change_password": false
  },
  "organization": {
    "id": "demo-org-1",
    "name": "Детский сад «Солнышко»"
  }
}
```

Когда Backend готов, mock заменяется без переписывания UI-моделей.

---

# 24. Что НЕ делать на Этапе 1

Не делать:

- список детей;
- карточку ребёнка;
- родителей;
- группы;
- сотрудников;
- посещаемость;
- объявления;
- настоящую статистику Dashboard;
- PARENT UI;
- TEACHER UI;
- СКУД;
- планшет;
- AI;
- платежи.

---

# 25. Порядок задач

## FRONT-01
Инициализация Next.js + TypeScript.

## FRONT-02
Environment + API client.

## FRONT-03
Базовые UI components.

## FRONT-04
Login page.

## FRONT-05
Auth state.

## FRONT-06
Mandatory change password page.

## FRONT-07
Protected routes.

## FRONT-08
AppShell / Sidebar / Header.

## FRONT-09
Role handling.

## FRONT-10
Technical Dashboard.

## FRONT-11
Error/loading states.

## FRONT-12
Responsive + README.

---

# 26. Тестовые сценарии

### Scenario 1
Неавторизованный пользователь открывает `/dashboard` → `/login`.

### Scenario 2
Неверный пароль → понятная ошибка, технические детали не показаны.

### Scenario 3
Временный пароль → `/change-password`.

### Scenario 4
Попытка вручную открыть `/dashboard` до смены → обратно `/change-password`.

### Scenario 5
Пароль изменён → Dashboard.

### Scenario 6
Refresh Dashboard → session сохраняется корректно.

### Scenario 7
Logout → Dashboard больше недоступен.

### Scenario 8
Blocked user → интерфейс не открывается.

---

# 27. Definition of Done

Frontend Этап 1 готов, когда:

- source-файлы соответствуют `docs/09-code-and-error-standards.md`;
- `npm run lint` проходит;
- `npm run build` проходит;

- login работает с реальным или утверждённым mock API;
- email нигде не требуется;
- password нигде не логируется;
- temporary password flow работает;
- protected routes работают;
- `/auth/me` используется как источник текущего пользователя;
- DIRECTOR и ADMIN корректно отображаются;
- layout работает;
- logout работает;
- desktop/tablet проверены;
- нет console errors;
- API types соответствуют общему контракту;
- README запуска актуален.

---

# 28. Результат

Frontend-разработчик передаёт:

1. запускаемый frontend;
2. `.env.example`;
3. Login;
4. Change Password;
5. Protected Routes;
6. Layout;
7. API client;
8. role handling;
9. mock data при необходимости;
10. README.

После этого Frontend может начинать Этап 2.
