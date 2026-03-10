\# GASQ ARCHITECTURE FREEZE



GasQ project architecture is frozen.



The following technology stack is final.



Backend:

FastAPI



Database:

PostgreSQL



ORM:

SQLAlchemy



Auth:

JWT authentication



Realtime:

WebSocket



Infrastructure:

Docker



Monitoring:

Prometheus

Sentry



Deployment:

Hetzner server



---



\# Project Rules



The following changes are NOT allowed:



\- changing backend framework

\- changing database

\- restructuring project architecture

\- rewriting queue system



Allowed changes:



\- fixing bugs

\- improving queue logic

\- adding new endpoints

\- improving realtime events



---



\# Development Policy



Work must follow rule:



one test → one fix.



No experimental rewrites.



Architecture stability is priority.

