# Проверить Stage 2 в браузере

Нужен установленный и запущенный Docker Desktop с Docker Compose, а также Git Bash. Данные в preview синтетические.

В Git Bash из папки `smart-garden`:

```bash
git fetch origin
git switch main
git pull --ff-only
bash scripts/start-preview.sh
```

Если локальной ветки `main` ещё нет, выполните `git switch --track origin/main` и пропустите `git pull --ff-only`.

После запуска откройте [http://localhost:3000/login](http://localhost:3000/login). Временные пароли `director-demo`, `admin-demo` и `stage2-director-demo` отображаются в терминале **только при первом создании** аккаунтов. Войдите под `stage2-director-demo`, смените пароль и проверьте разделы «Группы», «Дети», «Родители и законные представители». Синтетические группа, ребёнок, представитель и связь уже созданы; можно добавить новые записи через интерфейс. В карточке представителя можно создать PARENT аккаунт и увидеть временный пароль один раз. Выйдите, войдите под PARENT, смените пароль и проверьте `/parent`. API: [health](http://localhost:8000/api/v1/health) и [OpenAPI](http://localhost:8000/docs).

Повторный запуск `bash scripts/start-preview.sh` сохраняет аккаунты и новые пароли в локальном томе PostgreSQL. Если забыли пароль, нужен новый локальный тестовый том: команда ниже **удаляет только данные этой локальной preview-БД**, после чего запустите `bash scripts/start-preview.sh` ещё раз:

```bash
docker compose --env-file .env.preview -f docker-compose.yml -f docker-compose.preview.yml down -v
```

Чтобы просто остановить контейнеры, сохранив данные:

```bash
docker compose --env-file .env.preview -f docker-compose.yml -f docker-compose.preview.yml down
```

Не вводите реальные персональные данные в локальную preview версию. Родительский экран пока технический: данные детей ему не показываются.
