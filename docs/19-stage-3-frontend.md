# ТЗ Stage 3 — Frontend

**Источник решений:** `docs/17-stage-3-data-model-and-decisions.md`. **Контракт:** `docs/20-api-contract-stage-3.md`. Stage 1/2 интерфейс и auth lifecycle сохраняются.

## 1. Маршруты и роли

В навигации DIRECTOR/ADMIN активировать «Сотрудники» → `/employees` и «Посещаемость» → `/attendance`. Добавить `/employees/new`, `/employees/[id]`. DIRECTOR видит account controls сотрудника; ADMIN видит карточку, но не кнопки создания/сброса/блокировки учётной записи. PARENT не видит management shell и при прямом URL возвращается на `/parent`; Backend отдельно отклоняет его запросы.

## 2. Employee UI

Список: active по умолчанию, фильтр active/archived/all, поиск по ФИО на клиенте, ФИО, должность, статус, наличие ADMIN аккаунта. Loading, empty, safe error, retry. Создание/редактирование: фамилия, имя, необязательное отчество, должность. Телефон, email, адрес, дата рождения, документы и notes отсутствуют. После create открыть detail.

Detail: ФИО, должность, статус, edit, archive/restore с подтверждением. ADMIN не получает действие archive для карточки со связанным User; Backend также запрещает его. Для DIRECTOR при `account=null` кнопка «Выдать доступ администратора»; при существующем аккаунте username, status, must_change_password, reset/block/unblock. Одноразовый username+temporary password показывать только из ответа create/reset в отдельной карточке с явной кнопкой «Закрыть и скрыть пароль». После закрытия/ухода со страницы/refresh пароль не восстановить. Не складывать credentials в URL, storage, console или аналитику. Archive сотрудника с аккаунтом предупреждает, что доступ блокируется; restore не разблокирует его автоматически.

## 3. Attendance UI

Экран `/attendance`: по умолчанию текущая календарная дата пользователя, выбор date; фильтры группа, статус present/absent/unknown/all и ребёнок. Основной список после выбора даты показывает ФИО ребёнка, группу, статус, arrival/departure. Без записи показывать «Без отметки»; никаких фиктивных сохранённых строк. Для present — необязательные поля `HH:MM`, departure нельзя ввести без arrival или раньше него; для absent/unknown времена очищаются. Сохранение вызывает API и обновляет строку; во время запроса кнопка disabled. Показать безопасное сообщение об ошибке и retry. Не создавать автоматическую отметку только из открытия страницы.

Дата и время показываются как календарные значения без преобразования в часовой пояс браузера. Не добавлять причины отсутствия, medical fields, free text comment, импорт Excel, СКУД или планшет. Исторический group snapshot из ответа Backend не заменять текущей группой ребёнка. При архивном ребёнке история остаётся доступной через выбор даты/фильтр, но новая отметка запрещена — UI показывает текст ошибки сервера.

## 4. API и состояния

Отдельные modules `lib/api/employees.ts` и `lib/api/attendance.ts`, transport types в `types/stage3.ts`. Использовать общий клиент, cookie только HttpOnly, snake_case, ни в одном body не отправлять organization_id/actor UUID. Для списков и detail: loading/success/empty/error/retry; 404 показывать нейтрально, 403 без подробностей чужого сада. Кнопки реальные `button`, inputs связаны с label, ошибки доступны текстом/role, видимый focus. Desktop/tablet/mobile без горизонтального переполнения, действия доступны с клавиатуры.

## 5. Browser E2E

На синтетических данных: DIRECTOR создаёт Employee, выдаёт ADMIN аккаунт, видит пароль один раз; ADMIN входит, меняет пароль, не видит account controls и получает 403 от account API. DIRECTOR блокирует/архивирует и проверяет отзыв сессии. Затем создаёт/обновляет manual attendance `present`, исправляет на `absent`, видит `unknown` для ребёнка без записи; фильтры работают; PARENT UI/API запрещены. Проверить десктоп, планшет и mobile overflow, no page errors. Stage 1/2 тесты сохраняются.

## 6. Персональные данные — обязательный блок

Показывать только поля, нужные текущему экрану и роли; никаких причин отсутствия, медицинских сведений и свободных заметок. Не помещать ФИО/должность/посещаемость в URL query или логи браузера; только UUID, дату и enum-фильтры. Не сохранять формы и временные credentials в browser storage. Dev/demo screenshots — синтетические. Реальные данные не вводить до отдельной проверки по 152-ФЗ и подготовки пилота.

## Definition of Done

- Навигация и role-aware элементы соответствуют контракту; сервер остаётся источником авторизации.
- Employee CRUD/archive/restore, account controls DIRECTOR и одноразовая карточка работают.
- Attendance day view, фильтры и ручные отметки работают без mock.
- Loading/error/empty/retry, accessibility baseline и responsive проверены.
- `npm ci`, lint, build, Playwright Stage 1/2/3 и Docker preview зелёные.
