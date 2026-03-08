\# GASQ PROJECT BASELINE



System: GasQ – Queue \& Station Management  

Status: Architecture Frozen  

Purpose: Project baseline (similar to approved construction PSD)



This document fixes the architecture of the GasQ system and the current development state.



---



\# 1. SYSTEM PURPOSE



GasQ is a system for managing vehicle queues at fuel stations.



The system allows:



• Drivers to join fuel station queues  

• Operators to control pumps  

• Stations to manage traffic flow  

• Real-time queue monitoring  

• Notifications and analytics



Core workflow:



Driver → Queue → Pump → Fueling → Done



---



\# 2. SYSTEM ARCHITECTURE



Frontend

│

│ REST API + WebSocket

▼

FastAPI Backend

│

├ Queue Engine

├ Pump Management

├ Notification System

├ ETA Calculation

├ Audit Logs

├ Reports

└ Realtime Engine

│

▼

PostgreSQL Database



Monitoring:

Prometheus Metrics



Error tracking:

Sentry



---



\# 3. TECHNOLOGY STACK



Backend Framework:

FastAPI



Language:

Python 3.11+



Database:

PostgreSQL



ORM:

SQLAlchemy (async)



Realtime:

WebSocket



Monitoring:

Prometheus



Error Tracking:

Sentry



---



\# 4. BACKEND STRUCTURE



Project path:



gasq/backend/app



Structure:



app

│

├ api

│   ├ auth.py

│   ├ queue.py

│   ├ stations.py

│   ├ pumps.py

│   ├ reservations.py

│   ├ ratings.py

│   ├ reports.py

│   ├ users.py

│   ├ operator.py

│   ├ driver.py

│   ├ checkin.py

│   ├ ws\_queue.py

│   └ router.py

│

├ core

│   ├ config.py

│   ├ security.py

│   ├ lifespan.py

│   ├ deps.py

│   └ realtime.py

│

├ db

│   ├ engine.py

│   ├ session.py

│   ├ base.py

│   └ base\_class.py

│

├ models

│   ├ queue.py

│   ├ station.py

│   ├ pump.py

│   ├ user.py

│   ├ notification.py

│   ├ reservation.py

│   ├ rating.py

│   └ audit.py

│

├ services

│   ├ eta.py

│   ├ notify.py

│   ├ sms.py

│   ├ push\_fcm.py

│   ├ audit.py

│   └ no\_show\_loop.py

│

└ main.py



---



\# 5. CORE MODEL



Main entity:



QueueTicket



Fields:



id  

station\_id  

ticket\_no  

fuel\_type  

status  

driver\_phone  

driver\_user\_id  

source  



created\_at  

called\_at  

done\_at  



pump\_no  



check\_in\_at  



driver\_state  

heading\_at  

arrived\_at  



cancelled\_at  

cancel\_reason  



claim\_code



---



\# 6. QUEUE STATUSES



waiting  

called  

fueling  

done  

cancelled



Driver states:



idle  

heading  

arrived



---



\# 7. QUEUE WORKFLOW



Driver joins queue  

↓  

status = waiting  



Operator calls driver  

↓  

status = called  

pump assigned  



Driver arrives  

↓  

status = fueling  



Fueling finished  

↓  

status = done



Exceptions:



Driver cancels  

→ cancelled



Driver no-show  

→ cancelled



---



\# 8. MAIN API



Base path:



/api/v1



Queue endpoints:



POST /queue/join  

POST /queue/call-next  

POST /queue/start-fueling  

POST /queue/done  

POST /queue/cancel  

POST /queue/no-show  

POST /queue/recall  



GET /queue/panel  

GET /queue/stats  

GET /queue/history  

GET /queue/active  



GET /queue/ticket/{id}  

GET /queue/ticket/{id}/eta  



Driver:



POST /queue/driver-state  

POST /queue/check-in



---



\# 9. REALTIME SYSTEM



WebSocket endpoint:



/ws/queue/{station\_id}



Realtime events:



ticket\_called  

ticket\_joined  

ticket\_fueling  

ticket\_done  

ticket\_cancelled  



driver\_heading  

driver\_arrived



Purpose:



Operator panels update instantly.



---



\# 10. NOTIFICATION SYSTEM



Notifications table:



notifications



Types:



operator\_called  

ticket\_done  

ticket\_cancelled  

driver\_heading  

driver\_arrived



---



\# 11. MONITORING



System endpoints:



/health  

/metrics



Prometheus metrics:



http\_requests\_total  

http\_request\_duration\_seconds



---



\# 12. SECURITY



Authentication:

JWT tokens



Roles:



admin  

owner  

operator  

viewer  

driver



---



\# 13. CURRENT IMPLEMENTATION STATUS



Implemented modules:



Queue Engine  

Station Management  

Pump Control  

Driver Interaction  

Operator Panel API  

Notifications  

Ratings  

Reservations  

Reports  

Audit Logging  

SMS Service  

Push Service  

Realtime Queue  

Metrics  

Health Check



Backend readiness:



~80%



---



\# 14. FUTURE WORK



Frontend realtime integration  

Station queue display screen  

Mobile driver app  

Production deployment  

Load testing



---



\# 15. ARCHITECTURE RULES



Architecture is frozen.



Rules:



Do not redesign core queue model  

Do not change folder structure  

Do not change main workflow  



Future work must extend this architecture only.



---



END OF DOCUMENT

GasQ Project Baseline

