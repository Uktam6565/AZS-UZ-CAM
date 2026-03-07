\# GasQ Super Context



Project: GasQ — Gas Station Queue Management Platform



Repository: AZS-UZ-CAM



Backend stack:

FastAPI + PostgreSQL + SQLAlchemy Async + Docker



Backend path:

gasq/backend



Main backend entry:

app/main.py



API prefix:

api/v1



Core modules implemented:

auth

stations

pumps

queue system

notifications

ratings

audit logs

monitoring

metrics

structured logging



Monitoring:

Sentry

Prometheus metrics endpoint (/metrics)



Logging:

request\_id middleware

structured JSON logs



Core queue model:

QueueTicket



Queue fields:

station\_id

ticket\_no

fuel\_type

status

pump\_no

driver\_phone

driver\_user\_id

claim\_code

driver\_state

created\_at

called\_at

done\_at

cancelled\_at



Queue lifecycle:

waiting → called → fueling → done

exit states: cancelled / no\_show



Driver states:

idle → heading → arrived



Queue API:

POST /queue/join

GET /queue/panel

POST /queue/call-next

POST /queue/start-fueling

POST /queue/done

POST /queue/finish

POST /queue/recall

POST /queue/check-in

POST /queue/set-status

POST /queue/cancel

POST /queue/no-show

POST /queue/driver-state

GET /queue/ticket/{ticket\_id}

GET /queue/ticket/{ticket\_id}/eta

GET /queue/stats

GET /queue/history

GET /queue/active

GET /queue/station/{station\_id}/count



Security:

JWT authentication

role-based access

(admin, operator, owner, viewer)



Queue protections:

duplicate join protection

join cooldown anti-spam

unique ticket numbers per station

claim\_code driver access



Project status:

Backend ≈ 70–75% complete



Current development focus:

queue system stabilization

operator workflow

driver workflow

realtime queue updates



Important files:

app/main.py

app/api/queue.py

app/models/queue.py



Goal:

build scalable real-time gas station queue platform

