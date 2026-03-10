\# GasQ Backend Map



\## Backend structure



gasq/backend/app



core/

\- config.py

\- security.py

\- lifespan.py

\- realtime.py



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



\## Main API



Auth

/api/v1/auth/register

/api/v1/auth/login



Queue

/api/v1/queue/join

/api/v1/queue/panel

/api/v1/queue/call-next



Operator

/api/v1/operator/call\_next



Driver

/api/v1/driver/ticket



Stations

/api/v1/stations



---



\## Realtime



WebSocket queue updates



ws endpoints:

/ws/queue/{station\_id}



Broadcast events:

\- ticket\_called

\- queue\_updated



---



\## Monitoring



Endpoints:



/health

/metrics



Prometheus metrics enabled.



---



\## Current Focus



Fix queue panel state after call-next.

