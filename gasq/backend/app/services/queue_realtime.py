from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.queue import QueueTicket
from app.schemas.realtime import (
    QueueRealtimeEvent,
    QueueStationSnapshot,
    QueueTicketRealtimePayload,
)
from app.services.realtime_manager import realtime_manager


ACTIVE_STATUSES = {"waiting", "called", "fueling"}


def map_ticket(ticket: QueueTicket) -> QueueTicketRealtimePayload:
    return QueueTicketRealtimePayload(
        id=ticket.id,
        station_id=ticket.station_id,
        ticket_no=ticket.ticket_no,
        fuel_type=ticket.fuel_type,
        status=ticket.status,
        pump_no=ticket.pump_no,
        driver_phone=ticket.driver_phone,
        driver_user_id=ticket.driver_user_id,
        driver_state=ticket.driver_state,
        claim_code=ticket.claim_code,
        created_at=ticket.created_at,
        called_at=ticket.called_at,
        done_at=ticket.done_at,
        cancelled_at=ticket.cancelled_at,
    )


async def build_station_snapshot(session: AsyncSession, station_id: int) -> QueueStationSnapshot:
    waiting_count = await session.scalar(
        select(func.count()).select_from(QueueTicket).where(
            QueueTicket.station_id == station_id,
            QueueTicket.status == "waiting",
        )
    ) or 0

    called_count = await session.scalar(
        select(func.count()).select_from(QueueTicket).where(
            QueueTicket.station_id == station_id,
            QueueTicket.status == "called",
        )
    ) or 0

    fueling_count = await session.scalar(
        select(func.count()).select_from(QueueTicket).where(
            QueueTicket.station_id == station_id,
            QueueTicket.status == "fueling",
        )
    ) or 0

    active_count = await session.scalar(
        select(func.count()).select_from(QueueTicket).where(
            QueueTicket.station_id == station_id,
            QueueTicket.status.in_(ACTIVE_STATUSES),
        )
    ) or 0

    current_ticket_result = await session.execute(
        select(QueueTicket)
        .where(
            QueueTicket.station_id == station_id,
            QueueTicket.status.in_(("called", "fueling")),
        )
        .order_by(QueueTicket.called_at.asc().nullslast(), QueueTicket.created_at.asc())
        .limit(1)
    )
    current_ticket = current_ticket_result.scalar_one_or_none()

    next_tickets_result = await session.execute(
        select(QueueTicket)
        .where(
            QueueTicket.station_id == station_id,
            QueueTicket.status == "waiting",
        )
        .order_by(QueueTicket.ticket_no.asc())
        .limit(10)
    )
    next_tickets = next_tickets_result.scalars().all()

    return QueueStationSnapshot(
        station_id=station_id,
        waiting_count=waiting_count,
        called_count=called_count,
        fueling_count=fueling_count,
        active_count=active_count,
        current_ticket=map_ticket(current_ticket) if current_ticket else None,
        next_tickets=[map_ticket(t) for t in next_tickets],
    )


async def publish_station_event(
    session: AsyncSession,
    *,
    event: str,
    station_id: int,
    ticket: QueueTicket | None = None,
    payload: dict | None = None,
) -> None:
    snapshot = await build_station_snapshot(session, station_id)

    station_message = QueueRealtimeEvent(
        event=event,
        audience="station",
        station_id=station_id,
        ticket_id=ticket.id if ticket else None,
        at=datetime.now(timezone.utc),
        payload=payload or {},
        snapshot=snapshot,
    )
    await realtime_manager.broadcast_station(station_id, station_message.model_dump(mode="json"))

    if ticket:
        driver_message = QueueRealtimeEvent(
            event=event,
            audience="driver",
            station_id=station_id,
            ticket_id=ticket.id,
            at=datetime.now(timezone.utc),
            payload={
                **(payload or {}),
                "ticket": map_ticket(ticket).model_dump(mode="json"),
            },
            snapshot=snapshot,
        )
        await realtime_manager.broadcast_driver(ticket.id, driver_message.model_dump(mode="json"))