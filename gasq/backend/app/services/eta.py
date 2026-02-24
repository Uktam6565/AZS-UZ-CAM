from math import ceil
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.queue import QueueTicket
from app.models.station import Station


async def calc_eta_for_ticket(db: AsyncSession, ticket: QueueTicket) -> int:
    st = await db.get(Station, ticket.station_id)

    avg = int(getattr(st, "avg_service_min", 5) or 5)
    pumps = max(int(getattr(st, "pumps_count", 1) or 1), 1)

    res = await db.execute(
        select(func.count())
        .select_from(QueueTicket)
        .where(
            QueueTicket.station_id == ticket.station_id,
            QueueTicket.fuel_type == ticket.fuel_type,
            QueueTicket.status.in_(["waiting", "called"]),
            QueueTicket.id < ticket.id,
        )
    )
    ahead = int(res.scalar() or 0)
    return int(ceil((ahead / pumps) * avg))