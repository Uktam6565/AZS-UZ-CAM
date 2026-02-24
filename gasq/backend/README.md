# GasQ Backend (FastAPI)

## Что это
Backend API для:
- АЗС (станции)
- Колонки/зарядки
- Очередь (A001…)
- Рейтинги
- Бронирование

## Перед запуском
Нужны:
- Python 3.10+ (лучше 3.11)
- Docker (для PostgreSQL и Redis)

## Переменные окружения
Скопируй пример:
- backend/.env.example -> backend/.env

И при необходимости поменяй DATABASE_URL, JWT_SECRET_KEY и т.д.

## Старт инфраструктуры (PostgreSQL + Redis)
Из корня проекта (где docker-compose.yml):
```bash
docker compose up -d
