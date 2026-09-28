# Умный сад — Frontend, Stage 1–4 FROZEN

Next.js + TypeScript. Реализованы и заморожены Stage 1–4: auth/session flow, role-aware navigation, группы, дети, представители, сотрудники, посещаемость, Dashboard, Announcements, Audit и технический PARENT screen. Перед задачей читайте [`../AGENTS.md`](../AGENTS.md), затем [`../docs/CURRENT_STATE.md`](../docs/CURRENT_STATE.md), контракт текущего Stage и Issue.

## Запуск

Из корня репозитория:

```bash
cd frontend
cp .env.example .env.local
npm ci
npm run dev
```

На Windows в Git Bash `cp` работает. Откройте `http://localhost:3000/login`. Значение `NEXT_PUBLIC_API_BASE_URL` по умолчанию — `http://localhost:8000/api/v1`. Для рабочего входа запустите Backend с PostgreSQL и разрешённым CORS origin `http://localhost:3000`; тестовых паролей во Frontend нет. Синтетические demo-аккаунты создаются Backend seed-командой.

## Проверки

```bash
npm run lint
npm run build
```

Для ручной проверки Stage 1–4 используйте [`../PREVIEW.md`](../PREVIEW.md). Frontend не подменяет backend-сессию локальным mock: end-to-end проверка проходит по цепочке `Frontend → Backend → PostgreSQL`.

Автоматический сценарий `npm run test:e2e` использует реальный Backend, PostgreSQL и Chromium. Для локального запуска создайте синтетических пользователей через Backend seed, задайте их временные пароли только в переменных окружения `CI_DIRECTOR_PASSWORD` и `CI_ADMIN_PASSWORD`, запустите оба сервера и установите браузер командой `npx playwright install chromium`. В Pull Request эти действия выполняет интеграционный job GitHub Actions.

## API и данные

Frozen контракты: `../docs/03-api-contract-v0.1.md`, `../docs/15-api-contract-stage-2.md`, `../docs/20-api-contract-stage-3.md` и `../docs/25-api-contract-stage-4.md`. Все вызовы идут из `src/lib/api/` с `credentials: "include"`. Браузер отправляет HttpOnly cookie `smart_garden_session`; приложение не читает её, не сохраняет пароли, токены или данные форм объявлений в web storage. Организация и роль приходят от `/auth/me`. Сообщения об ошибках строятся из фиксированных безопасных строк, серверный traceback не показывается.

## Персональные данные (обязательно)

В разработке и тестировании используйте только синтетические учётные записи. Не добавляйте реальные данные детей, родителей и сотрудников в код, скриншоты, URL, аналитику и логи. Пароли и полный ответ авторизации не логируются. Frontend отображает только контекст текущего пользователя; доступ и изоляцию организаций проверяет Backend. До пилота необходима отдельная проверка организационных и правовых требований к обработке ПДн по `docs/05-personal-data-baseline.md`.
