\# GASQ MASTER CONTEXT



\## Project

GasQ — система управления очередью автомобилей на автозаправочных станциях.



Цель:

уменьшить очереди на АЗС и дать оператору realtime управление колонками.



---



\# Architecture



Backend:

FastAPI (Python)



Database:

PostgreSQL



ORM:

SQLAlchemy



Migrations:

Alembic



Auth:

JWT authentication



Realtime:

WebSocket



Monitoring:

Prometheus metrics

Sentry monitoring



Deployment:

Docker

Hetzner server (planned)



---



\# Backend structure



gasq/backend/app



core/

\- config.py

\- security.py

\- realtime.py

\- lifespan.py



db/

\- engine.py

\- session.py

\- base.py



models/

\- user.py

\- station.py

\- pump.py

\- queue.py

\- notification.py



api/

\- auth.py

\- stations.py

\- queue.py

\- operator.py

\- driver.py

\- users.py

\- admin.py

\- reports.py



api/routes/

\- notifications.py



services/

\- eta.py

\- notify.py

\- sms.py

\- push\_fcm.py

\- no\_show\_loop.py



main.py

router.py



---



\# Core API



Auth



POST /api/v1/auth/register

POST /api/v1/auth/login



Queue



POST /api/v1/queue/join

GET /api/v1/queue/panel

POST /api/v1/queue/call-next



Operator



POST /api/v1/operator/call\_next



Driver



GET /api/v1/driver/ticket



Stations



GET /api/v1/stations



---



\# Realtime



WebSocket endpoint:



/ws/queue/{station\_id}



Events:



ticket\_called

queue\_updated



Realtime manager:



app/core/realtime.py



---



\# Monitoring



System endpoints



GET /health

GET /metrics



Prometheus metrics enabled.



Sentry monitoring enabled.



---



\# Confirmed Working



Backend successfully tested.



Working endpoints:



/health

/metrics

auth/register

auth/login

queue/join

queue/panel

queue/call-next



JWT authentication working.



Database operations working.



Queue system working.



Operator flow working.



---



\# Known Issue



After call-next:



queue decreases correctly,

but queue panel may not show active ticket in pumps.current.



stats sometimes show cancelled=1 unexpectedly.



Panel logic requires debugging.



---



\# Development Rules



Architecture is FIXED.



Do NOT:



\- change technology stack

\- rewrite architecture

\- restructure project folders



Allowed:



\- fix bugs

\- improve queue logic

\- add missing features



Development workflow:



one test → one fix.



---



\# Current Task



Debug queue panel state after call-next.



Investigate:



panel() logic

pump assignment

queue status transitions

