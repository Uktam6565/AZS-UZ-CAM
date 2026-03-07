\# GasQ Architecture Map



\## Project

GasQ = gas station queue management platform.



Purpose:

\- drivers join queue remotely

\- operators call next car

\- station manages pumps and flow

\- backend tracks queue lifecycle, notifications, metrics, logs



---



\## Tech Stack



\### Backend

\- FastAPI

\- PostgreSQL

\- SQLAlchemy Async

\- Alembic



\### Runtime / Infra

\- Docker

\- Docker Compose

\- Nginx

\- Gunicorn + Uvicorn workers



\### Observability

\- Prometheus

\- Sentry

\- Structured JSON logging

\- Request ID tracing



\### Security

\- JWT auth

\- role-based access

\- rate limiting

\- real IP support via Nginx



---



\## Main Backend Entry



`gasq/backend/app/main.py`



Responsibilities:

\- FastAPI app init

\- middleware

\- logging

\- Prometheus metrics

\- Sentry init

\- request tracing

\- `/health`

\- `/metrics`

\- API router mount at `/api/v1`



---



\## Main API Prefix



`/api/v1`



Examples:

\- `/api/v1/auth/...`

\- `/api/v1/queue/...`

\- `/api/v1/stations/...`



---



\## Core Domain



\### Main actors

\- Driver

\- Operator

\- Owner

\- Admin

\- Viewer



\### Main station flow

Driver -> joins queue -> operator calls -> driver arrives -> fueling starts -> fueling ends



---



\## Main Models



\### User

Stores users and roles.



Roles:

\- admin

\- operator

\- owner

\- viewer

\- driver



\### Station

Gas station entity.



\### Pump

Physical fuel pump / column.



\### QueueTicket

Main queue entity.



Important fields:

\- `station\_id`

\- `ticket\_no`

\- `fuel\_type`

\- `status`

\- `pump\_no`

\- `claim\_code`

\- `driver\_phone`

\- `driver\_user\_id`

\- `driver\_state`

\- `created\_at`

\- `called\_at`

\- `done\_at`

\- `cancelled\_at`



\### Notification

System notifications for queue events.



\### Audit

Audit trail of important actions.



\### Rating

Feedback / rating logic.



\### Reservation

Reservation-related data.



---



\## Queue Status Lifecycle



`waiting -> called -> fueling -> done`



Possible exits:

\- `cancelled`

\- `no\_show` cancellation flow



Driver state:

\- `idle`

\- `heading`

\- `arrived`



---



\## Main Queue API



File:

`gasq/backend/app/api/queue.py`



Important endpoints:

\- `POST /queue/join`

\- `GET /queue/panel`

\- `POST /queue/call-next`

\- `POST /queue/start-fueling`

\- `POST /queue/done`

\- `POST /queue/finish`

\- `POST /queue/recall`

\- `POST /queue/check-in`

\- `POST /queue/set-status`

\- `POST /queue/cancel`

\- `POST /queue/no-show`

\- `POST /queue/driver-state`

\- `GET /queue/ticket/{ticket\_id}`

\- `GET /queue/ticket/{ticket\_id}/eta`

\- `GET /queue/stats`

\- `GET /queue/history`

\- `GET /queue/active`

\- `GET /queue/station/{station\_id}/count`



---



\## Queue Protection Logic



Implemented:

\- duplicate join protection

\- join cooldown anti-spam

\- unique ticket number per station

\- claim\_code-based ticket access

\- status-based transition logic



---



\## Auth / Security



\### Auth

JWT-based authentication.



\### Access control

Role-based access on endpoints.



\### Protection

\- auth rate limiting

\- brute force protection

\- Nginx real IP support

\- request-level tracing



---



\## Monitoring / Observability



\### Health

`/health`

\- backend health

\- database connectivity check



\### Metrics

`/metrics`

Prometheus-compatible metrics.



Collected metrics:

\- `http\_requests\_total`

\- `http\_request\_duration\_seconds`



\### Logging

Structured JSON request logging:

\- request\_id

\- ip

\- method

\- endpoint

\- status

\- latency\_ms



\### Error monitoring

Sentry SDK integrated.



---



\## Production Runtime



\### App server

Gunicorn + Uvicorn workers



\### Reverse proxy

Nginx



\### Containers

\- postgres

\- backend

\- nginx



\### Healthchecks

\- postgres healthcheck

\- backend healthcheck



---



\## Important Files



\### Core

\- `gasq/backend/app/main.py`

\- `gasq/backend/app/core/config.py`

\- `gasq/backend/app/core/security.py`



\### API

\- `gasq/backend/app/api/router.py`

\- `gasq/backend/app/api/auth.py`

\- `gasq/backend/app/api/queue.py`



\### Models

\- `gasq/backend/app/models/queue.py`

\- `gasq/backend/app/models/station.py`

\- `gasq/backend/app/models/pump.py`

\- `gasq/backend/app/models/user.py`



\### Infra

\- `docker-compose.prod.yml`

\- `deploy/nginx/nginx.conf`

\- `gasq/backend/start.sh`



---



\## Current State



Backend status:

\- production-ready foundation mostly done

\- queue system already partially implemented

\- observability and monitoring strong

\- infra and deployment base prepared



Approx progress:

\- backend platform: high readiness

\- product/business workflow: in progress



---



\## Next Product Priorities



1\. queue workflow stabilization

2\. operator panel refinement

3\. driver view / ticket tracking

4\. realtime queue updates

5\. notifications flow

6\. station operational analytics

