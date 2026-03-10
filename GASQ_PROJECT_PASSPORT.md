\# GASQ PROJECT PASSPORT



\## Project Name

GasQ — Gas Station Queue Management System



\## Project Goal

GasQ is a system for managing vehicle queues at gas stations.



The system must allow:



\- drivers to join queue remotely

\- operators to call next vehicle

\- station staff to assign pumps

\- realtime queue updates

\- notifications and analytics



---



\# 1. TECHNOLOGY STACK



Backend:

\- Python 3.11

\- FastAPI



Database:

\- PostgreSQL



ORM:

\- SQLAlchemy (async)



Migrations:

\- Alembic



Auth:

\- JWT authentication



Realtime:

\- WebSocket



Monitoring:

\- Prometheus

\- Sentry



Infrastructure:

\- Docker

\- GitHub Actions

\- Hetzner deployment planned



---



\# 2. ARCHITECTURE STATUS



Architecture is FIXED.



Do NOT change:



\- backend framework

\- database

\- ORM

\- project folder structure

\- queue core model

\- project technology stack



Allowed:



\- bug fixes

\- business logic improvements

\- new endpoints

\- realtime improvements

\- deployment work



Development rule:



one test → one fix



No architecture rewrites.



---



\# 3. PROJECT STRUCTURE



Main backend path:



gasq/backend/app



Main folders:



\- api

\- core

\- db

\- models

\- services



Main files:



\- main.py

\- api/router.py

\- api/auth.py

\- api/queue.py

\- api/operator.py

\- api/driver.py

\- api/ws\_queue.py

\- models/queue.py

\- core/realtime.py



---



\# 4. CORE DOMAIN



Main entity:

QueueTicket



Important fields:



\- id

\- station\_id

\- ticket\_no

\- fuel\_type

\- status

\- driver\_phone

\- driver\_user\_id

\- pump\_no

\- claim\_code

\- created\_at

\- called\_at

\- done\_at

\- cancelled\_at

\- cancel\_reason

\- driver\_state

\- heading\_at

\- arrived\_at

\- check\_in\_at



Queue statuses:



\- waiting

\- called

\- fueling

\- done

\- cancelled



Driver states:



\- idle

\- heading

\- arrived



---



\# 5. MAIN API



Base prefix:



/api/v1



Auth:

\- POST /auth/register

\- POST /auth/login



Queue:

\- POST /queue/join

\- GET /queue/panel

\- POST /queue/call-next

\- POST /queue/start-fueling

\- POST /queue/done

\- POST /queue/cancel

\- POST /queue/no-show

\- POST /queue/recall

\- GET /queue/stats

\- GET /queue/history

\- GET /queue/active

\- GET /queue/ticket/{ticket\_id}

\- GET /queue/ticket/{ticket\_id}/eta

\- POST /queue/driver-state

\- POST /queue/check-in



Realtime:

\- /ws/queue/{station\_id}



Monitoring:

\- GET /health

\- GET /metrics



---



\# 6. CONFIRMED WORKING



The following functionality has been tested and confirmed working:



\- backend starts successfully

\- PostgreSQL connection works

\- /health works

\- /metrics works

\- auth/register works

\- auth/login works

\- JWT generation works

\- queue/join works

\- operator register works

\- operator login works

\- queue/panel works with operator JWT

\- queue/call-next works



Confirmed by live API testing.



---



\# 7. CURRENT ISSUE



After call-next:



\- waiting queue decreases correctly

\- call-next returns correct ticket, status, pump\_no

\- but queue panel may not show active ticket in pumps.current

\- stats may show cancelled=1 unexpectedly



This means:



core queue flow works,

but panel state aggregation logic requires debugging.



Current task:



debug queue panel after call-next.



Investigate:



\- panel() active\_by\_pump logic

\- ticket status transitions

\- no\_show side effects

\- pump current mapping



---



\# 8. REALTIME STATUS



Realtime architecture already added:



\- core/realtime.py

\- api/ws\_queue.py

\- WebSocket broadcast manager

\- queue event broadcast for ticket\_called



Realtime system exists but still requires stabilization and frontend integration.



---



\# 9. MONITORING STATUS



Implemented:



\- Prometheus metrics

\- request logging

\- structured JSON logs

\- request\_id tracing

\- Sentry monitoring



System monitoring is already at strong production level.



---



\# 10. PROJECT READINESS



Estimated backend readiness:



~80%



Ready:

\- architecture

\- auth

\- queue core

\- operator flow

\- monitoring

\- metrics

\- logging



In progress:

\- realtime polishing

\- panel consistency

\- frontend realtime integration



Not finished:

\- production deployment

\- final full-system test on server



---



\# 11. LOCAL RUN



Correct backend run path:



C:\\Users\\matku\\Desktop\\AZS-UZ-CAM\\gasq\\backend



Correct command:



python -m uvicorn app.main:app --reload



Optional helper scripts may be used:

\- RUN\_GASQ\_BACKEND.bat

\- OPEN\_GASQ\_DOCS.bat

\- OPEN\_GASQ\_HEALTH.bat

\- OPEN\_GASQ\_METRICS.bat

\- TEST\_GASQ\_WS.bat



---



\# 12. CHAT TRANSFER RULE



When continuing in a new AI chat:



1\. Read this file first

2\. Do not redesign the architecture

3\. Continue only from current confirmed state

4\. Work step by step

5\. One test → one step



---



\# 13. NEXT TASK



Immediate next task:



Fix queue panel state inconsistency after call-next.



After that:



\- verify pumps.current rendering

\- verify called ticket visibility

\- verify stats correctness

\- test WebSocket realtime update

\- connect frontend realtime flow



---



\# END OF PASSPORT

GasQ architecture is frozen.

Continue development without redesign.

