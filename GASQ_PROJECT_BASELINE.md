\# GasQ Project Baseline



\## Project

GasQ — система управления очередью на автозаправочных станциях.



Цель:

управление потоком автомобилей, сокращение очередей и realtime управление колонками.



---



\# Technology Stack



Backend:

\- Python

\- FastAPI

\- SQLAlchemy

\- PostgreSQL

\- Alembic



Realtime:

\- WebSocket



Infrastructure:

\- Docker

\- GitHub

\- Hetzner (deployment)



Monitoring:

\- Prometheus metrics

\- Sentry monitoring



---



\# Core Modules



Auth

\- register

\- login

\- JWT authentication



Queue

\- join queue

\- call next

\- queue panel



Operator

\- управление колонками

\- вызов автомобиля



Driver

\- получение талона

\- статус очереди



Stations

\- управление АЗС

\- управление колонками



Notifications

\- push

\- sms



---



\# Current Status



Backend запускается.



Работают:



\- /health

\- /metrics

\- auth/register

\- auth/login

\- queue/join

\- queue/panel

\- queue/call-next



Realtime и panel логика требуют доработки.



---



\# Development Rule



Архитектура зафиксирована.



Запрещено:

\- менять стек

\- переписывать архитектуру

\- экспериментировать со структурой проекта



Разрешено:

\- исправлять баги

\- улучшать бизнес-логику

\- добавлять функции.

