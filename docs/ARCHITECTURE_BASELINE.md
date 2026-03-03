GasQ v15 — стабильная версия заархивирована. Backend: FastAPI auth (JWT) роли (admin/operator/owner/driver) queue (join / call-next / panel) SSE для driver auto no-show cleanup работает check-in работает Frontend: admin / driver / terminal Leaflet карта PWA включён vendor только leaflet проект почищен (без .venv, без мусора) Хочу: Зафиксировать архитектуру как базовую Сделать структуру production-ready Дальше идти строго по плану Продолжаем с v15, не с нуля.



1\) Базовая архитектура v15 (фиксируем как неизменяемое ядро)

Backend (FastAPI)



Модули/фичи ядра:



JWT auth



Роли: admin / operator / owner / driver



Queue: join / call-next / panel



SSE для driver



auto no-show cleanup



check-in



Правило: дальше мы не переписываем бизнес-логику очереди/ролей/driver-flow без причины. Любые изменения — только через маленькие PR-шаги и тесты.



Frontend (статический)



admin / driver / terminal



Leaflet карта (vendor только leaflet)



PWA включен (manifest + service-worker)



Правило: фронт остаётся статикой (HTML/JS) — можно улучшать структуру/сборку, но без “переезда” на тяжёлый фреймворк, пока нет нужды.



2\) Production-ready структура (что добавляем вокруг ядра)

A) Репозиторий и папки



Добавляем сверху “обвязку”, не трогая смысл gasq/backend/app/\*:



deploy/



nginx/ (конфиги)



systemd/ (если деплой на VPS)



certbot/ (если нужен TLS)



scripts/



backup\_db.sh, restore\_db.sh, healthcheck.sh



docs/



ARCHITECTURE\_BASELINE.md



RUNBOOK.md (как запускать/восстанавливать/обслуживать)



.github/workflows/ (CI: lint + tests + build)



B) Backend production



Dockerfile для backend (multi-stage опционально)



запуск через gunicorn + uvicorn workers (не просто uvicorn --reload)



нормальные health endpoints:



/health (быстрый)



/ready (проверка БД)



централизованный logging (структурно + уровни)



настройки через .env + config.py, но:



отдельные профили DEV/PROD



запрет DEBUG в PROD



CORS/TrustedHost/ProxyHeaders



C) Frontend production



сборки как таковой нет (и это ок), но:



отдача через nginx (gzip, cache headers, immutable для vendor)



правильные cache-control для service-worker.js (чтобы обновления не “залипали”)



D) Docker Compose: dev vs prod



docker-compose.yml оставить для dev



добавить docker-compose.prod.yml:



backend



db (Postgres)



nginx (reverse proxy + static frontend)



(опционально) redis если появится фон/кэш



E) Миграции и данные



Alembic — уже есть, отлично.



“операционные” команды:



alembic upgrade head



создание пользователей/ролей (если надо — отдельный admin script)



регулярный backup БД (скрипт + cron/systemd timer)



3\) “Строго по плану”: дорожная карта от v15 → production

Этап 0 — фиксация базы (1 коммит)



Git tag:



git tag v15.0.0

git push --tags



Создать файл docs/ARCHITECTURE\_BASELINE.md и записать туда то, что ты написал (и то, что я выше зафиксировал).



✅ Результат: v15 становится “точкой истины”.

