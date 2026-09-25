# Умный сад — Frontend, этап 1

Next.js + TypeScript. Реализованы `/login`, `/change-password`, `/dashboard`, `/403`, `/404`, единый API-клиент, проверка сессии через `/auth/me` и выход. Разделы детей, групп, родителей и прочие бизнес-разделы пока выключены согласно `docs/02-stage-1-frontend.md`.

## Запуск

Из корня репозитория:

```bash
cd frontend
cp .env.example .env.local
npm ci
npm run dev
```

На Windows в Git Bash `cp` работает. Откройте `http://localhost:3000/login`. Значение `NEXT_PUBLIC_API_BASE_URL` по умолчанию — `http://localhost:8000/api/v1`. Для рабочего входа запустите Backend Stage 1 с PostgreSQL и разрешённым CORS origin `http://localhost:3000`; тестовых паролей во Frontend нет. Учетные записи `director-demo` и `admin-demo` создаются Backend seed-командой.

## Проверки

```bash
npm run lint
npm run build
```

Проверьте вручную сценарии 1–8 из `docs/02-stage-1-frontend.md` после запуска Backend. Ветка Frontend сама по себе не подменяет backend-сессию локальным mock: end-to-end проверка проходит на интеграционном этапе `Frontend → Backend → PostgreSQL`.

Автоматический сценарий `npm run test:e2e` использует реальный Backend, PostgreSQL и Chromium. Для локального запуска создайте синтетических пользователей через Backend seed, задайте их временные пароли только в переменных окружения `CI_DIRECTOR_PASSWORD` и `CI_ADMIN_PASSWORD`, запустите оба сервера и установите браузер командой `npx playwright install chromium`. В Pull Request эти действия выполняет интеграционный job GitHub Actions.

## API и данные

Контракт: `docs/03-api-contract-v0.1.md`. Все вызовы идут из `src/lib/api/` с `credentials: "include"`. Браузер отправляет HttpOnly cookie `smart_garden_session`; приложение не читает её, не сохраняет пароли или токены в web storage. Организация и роль приходят от `/auth/me`. Сообщения об ошибках строятся из фиксированных безопасных строк, серверный traceback не показывается.

## Персональные данные (обязательно)

В разработке и тестировании используйте только синтетические учётные записи. Не добавляйте реальные данные детей, родителей и сотрудников в код, скриншоты, URL, аналитику и логи. Пароли и полный ответ авторизации не логируются. Frontend отображает только контекст текущего пользователя; доступ и изоляцию организаций проверяет Backend. До пилота необходима отдельная проверка организационных и правовых требований к обработке ПДн по `docs/05-personal-data-baseline.md`.
