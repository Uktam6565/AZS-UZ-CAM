\# GASQ PROJECT — CHAT CONTEXT



This document is provided to give full context of the GasQ system to AI assistants.



IMPORTANT RULE:



The project architecture is FIXED.

Do not redesign or restructure the system.

Only help continue development.



---



\# Project Overview



GasQ is a Queue Management System for Gas Stations.



Drivers join a queue before arriving at the station.

Operators call drivers to specific pumps.

The system manages real-time queue updates.



The system consists of:



Backend API

Realtime queue updates

Operator dashboard

Driver mobile interface

Notifications

Analytics



---



\# Technology Stack



Backend



FastAPI

Python 3.11

SQLAlchemy

PostgreSQL

WebSockets



Monitoring



Prometheus

Structured logging

Request ID

Sentry monitoring



Infrastructure



Docker

GitHub CI

Planned deployment: Hetzner Cloud



---



\# Backend Structure



backend/app



main.py

api/

models/

services/

core/

db/



---



\# Database Models



User

Station

Pump

QueueTicket

Reservation

Notification

Rating

Audit



---



\# QueueTicket Model



Fields include:



station\_id

ticket\_no

status

fuel\_type

driver\_phone

pump\_no

called\_at

done\_at

created\_at



Driver states



idle

heading

arrived



Queue statuses



waiting

called

fueling

done

cancelled



---



\# Implemented Features



Authentication

Driver queue join

Operator call next

Pump assignment

Driver check-in

Queue cancellation

Reservations

Ratings

Notifications

Audit logs

Reports

SMS service

Push notifications

Health check

Prometheus metrics

Structured logging

Request ID tracking



---



\# Realtime System



WebSocket queue updates.



Events include



ticket\_called

queue\_updated



Realtime broadcast manager implemented.



Frontend will subscribe to station queue channel.



---



\# Current Development Stage



Backend is approximately 80% complete.



Core system already implemented.



Remaining work mainly involves



Realtime stabilization

Frontend realtime integration

Production deployment



---



\# Current Issue



The system is experiencing environment-related issues:



Python module imports

Package dependencies

Circular imports



These are NOT architectural problems.



Architecture must remain unchanged.



---



\# Development Goal



Stabilize backend runtime.



Finish realtime queue updates.



Connect realtime to frontend dashboard.



Prepare production deployment.



---



\# Important Development Rule



DO NOT



Redesign architecture

Change folder structure

Replace technologies



ONLY



Fix issues

Continue development

Complete missing components.



---



\# Project Repository



GitHub repository contains full backend code.



Architecture baseline is documented in:



GASQ\_PROJECT\_BASELINE.md

GASQ\_BACKEND\_MAP.md



These files define the system structure.

