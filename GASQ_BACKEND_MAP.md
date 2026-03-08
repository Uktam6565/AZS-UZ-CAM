\# GASQ BACKEND MAP



Quick architecture overview of the GasQ backend.



Purpose: understand the system in 20 seconds.



---



\# SYSTEM FLOW



Driver / Operator / Station Screen

&nbsp;       │

&nbsp;       │ REST API

&nbsp;       ▼

FastAPI Backend

&nbsp;       │

&nbsp;       ├ Queue Engine

&nbsp;       ├ Pump Control

&nbsp;       ├ Notification System

&nbsp;       ├ ETA Service

&nbsp;       ├ Audit Logging

&nbsp;       └ Realtime Engine

&nbsp;       │

&nbsp;       ▼

PostgreSQL Database



---



\# BACKEND MODULES



API Layer



auth

queue

stations

pumps

reservations

ratings

reports

users

operator

driver

checkin

ws\_queue



---



\# CORE MODULES



config

security

lifespan

deps

realtime



---



\# DATABASE MODELS



QueueTicket

Station

Pump

User

Notification

Reservation

Rating

AuditLog



---



\# SERVICES



eta

notify

sms

push\_fcm

audit

no\_show\_loop



---



\# QUEUE WORKFLOW



Driver joins queue

&nbsp;       │

&nbsp;       ▼

waiting

&nbsp;       │

&nbsp;       ▼

Operator calls driver

&nbsp;       │

&nbsp;       ▼

called

&nbsp;       │

&nbsp;       ▼

fueling

&nbsp;       │

&nbsp;       ▼

done



Exceptions



cancelled

no-show



---



\# REALTIME SYSTEM



WebSocket endpoint



/ws/queue/{station\_id}



Realtime events



ticket\_called

ticket\_joined

ticket\_fueling

ticket\_done

ticket\_cancelled

driver\_heading

driver\_arrived



---



\# MONITORING



Prometheus metrics



/metrics



Health endpoint



/health



---



END OF FILE

GasQ Backend Map

