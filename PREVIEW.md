# Проверить этап 1 в браузере

Нужен установленный и запущенный Docker Desktop с Docker Compose, а также Git Bash. Данные в этой версии синтетические. Пока проверяем Pull Request #31, используйте ветку `integration/stage-1-auth`.

В Git Bash из папки `smart-garden`:

```bash
git fetch origin
git switch integration/stage-1-auth
git pull --ff-only
bash scripts/start-preview.sh
```

Если ветки ещё нет локально, вместо `git switch integration/stage-1-auth` выполните `git switch --track origin/integration/stage-1-auth` и пропустите `git pull --ff-only`.

После запуска откройте [http://localhost:3000/login](http://localhost:3000/login). Пароли `director-demo` и `admin-demo` отображаются в терминале **только при первом создании** аккаунтов. Войдите любым из них, задайте новый пароль по запросу и проверьте страницу `/dashboard` и выход из системы. API: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health) и [http://localhost:8000/docs](http://localhost:8000/docs).

Повторный запуск `bash scripts/start-preview.sh` сохраняет аккаунты и новые пароли в локальном томе PostgreSQL. Если забыли пароль, нужен новый локальный тестовый том: команда ниже **удаляет только данные этой локальной preview-БД**, после чего запустите `bash scripts/start-preview.sh` ещё раз:

```bash
docker compose --env-file .env.preview -f docker-compose.yml -f docker-compose.preview.yml down -v
```

Чтобы просто остановить контейнеры, сохранив данные:

```bash
docker compose --env-file .env.preview -f docker-compose.yml -f docker-compose.preview.yml down
```

На этом этапе доступны вход, смена временного пароля, техническая главная страница и выход. Учёт детей и другие разделы появятся на следующих этапах по ТЗ. Не вводите реальные персональные данные в эту локальную версию.
