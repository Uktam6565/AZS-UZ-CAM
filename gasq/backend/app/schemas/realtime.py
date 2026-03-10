from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field


QueueEventType = Literal[
    "queue.joined",
    "queue.called",
    "queue.recalled",
    "queue.check_in",
    "queue.driver_state_changed",
    "queue.fueling_started",
    "queue.done",
    "queue.finished",
    "queue.cancelled",
    "queue.no_show",
    "queue.status_changed",
    "queue.snapshot",
]

AudienceType = Literal["station", "operator", "driver", "admin"]


class QueueTicketRealtimePayload(BaseModel):
    id: int
    station_id: int
    ticket_no: str
    fuel_type: str | None = None
    status: str
    pump_no: int | None = None
    driver_phone: str | None = None
    driver_user_id: int | None = None
    driver_state: str | None = None
    claim_code: str | None = None
    created_at: datetime
    called_at: datetime | None = None
    done_at: datetime | None = None
    cancelled_at: datetime | None = None


class QueueStationSnapshot(BaseModel):
    station_id: int
    waiting_count: int = 0
    called_count: int = 0
    fueling_count: int = 0
    active_count: int = 0
    current_ticket: QueueTicketRealtimePayload | None = None
    next_tickets: list[QueueTicketRealtimePayload] = Field(default_factory=list)


class QueueRealtimeEvent(BaseModel):
    event: QueueEventType
    audience: AudienceType
    station_id: int
    ticket_id: int | None = None
    at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)
    snapshot: QueueStationSnapshot | None = None