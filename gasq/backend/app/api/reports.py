import csv
import io
from datetime import datetime, date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.station import Station
from app.models.queue import QueueTicket

router = APIRouter(prefix="/reports", tags=["reports"])


def _parse_date(d: Optional[str]) -> Optional[date]:
    if not d:
        return None
    return datetime.strptime(d, "%Y-%m-%d").date()


@router.get("/summary", response_model=dict)
async def summary(
    station_id: int = Query(...),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    station = await db.get(Station, station_id)
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")

    df = _parse_date(date_from)
    dt = _parse_date(date_to)

    stmt_base = select(QueueTicket).where(QueueTicket.station_id == station_id)

    # Фильтр по диапазону дат (по created_at)
    if df:
        start_dt = datetime.combine(df, datetime.min.time())
        stmt_base = stmt_base.where(QueueTicket.created_at >= start_dt)
    if dt:
        end_dt = datetime.combine(dt, datetime.max.time())
        stmt_base = stmt_base.where(QueueTicket.created_at <= end_dt)

    # totals
    total_q = await db.execute(select(func.count()).select_from(stmt_base.subquery()))
    total_tickets = int(total_q.scalar() or 0)

    called_q = await db.execute(
        select(func.count()).select_from(
            stmt_base.where(QueueTicket.status.in_(["called", "fueling", "done"])).subquery()
        )
    )
    called = int(called_q.scalar() or 0)

    waiting_q = await db.execute(
        select(func.count()).select_from(
            stmt_base.where(QueueTicket.status == "waiting").subquery()
        )
    )
    waiting = int(waiting_q.scalar() or 0)

    # avg wait seconds: called_at - created_at (только где called_at не null)
    avg_q = await db.execute(
        select(
            func.avg(
                func.extract("epoch", (QueueTicket.called_at - QueueTicket.created_at))
            )
        ).where(
            QueueTicket.station_id == station_id,
            QueueTicket.called_at.isnot(None),
            *( [QueueTicket.created_at >= datetime.combine(df, datetime.min.time())] if df else [] ),
            *( [QueueTicket.created_at <= datetime.combine(dt, datetime.max.time())] if dt else [] ),
        )
    )
    avg_wait_seconds = avg_q.scalar()
    avg_wait_seconds = int(avg_wait_seconds) if avg_wait_seconds else 0

    # by fuel
    by_fuel_q = await db.execute(
        select(QueueTicket.fuel_type, func.count())
        .where(QueueTicket.station_id == station_id)
        .group_by(QueueTicket.fuel_type)
    )

    # применим те же date-фильтры к by_fuel
    if df or dt:
        stmt = select(QueueTicket.fuel_type, func.count()).where(QueueTicket.station_id == station_id)
        if df:
            stmt = stmt.where(QueueTicket.created_at >= datetime.combine(df, datetime.min.time()))
        if dt:
            stmt = stmt.where(QueueTicket.created_at <= datetime.combine(dt, datetime.max.time()))
        stmt = stmt.group_by(QueueTicket.fuel_type)
        by_fuel_q = await db.execute(stmt)

    rows = by_fuel_q.all()
    by_fuel = { (r[0] or "unknown"): int(r[1]) for r in rows }

    return {
        "station_id": station_id,
        "station_name": station.name,
        "date_from": date_from,
        "date_to": date_to,
        "total_tickets": total_tickets,
        "called": called,
        "waiting": waiting,
        "avg_wait_seconds": avg_wait_seconds,
        "by_fuel": by_fuel,
        "generated_at": datetime.utcnow().isoformat(),
    }


@router.get("/export/csv")
async def export_csv(
    station_id: int = Query(...),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    station = await db.get(Station, station_id)
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")

    df = _parse_date(date_from)
    dt = _parse_date(date_to)

    stmt = select(QueueTicket).where(QueueTicket.station_id == station_id)

    if df:
        stmt = stmt.where(QueueTicket.created_at >= datetime.combine(df, datetime.min.time()))
    if dt:
        stmt = stmt.where(QueueTicket.created_at <= datetime.combine(dt, datetime.max.time()))

    stmt = stmt.order_by(QueueTicket.id.asc())
    res = await db.execute(stmt)
    tickets = res.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "ticket_no", "fuel_type", "status", "created_at", "called_at", "station_id"])
    for t in tickets:
        writer.writerow([
            t.id,
            t.ticket_no,
            t.fuel_type,
            t.status,
            t.created_at.isoformat() if t.created_at else "",
            t.called_at.isoformat() if t.called_at else "",
            t.station_id
        ])

    output.seek(0)
    filename = f"gasq_report_station_{station_id}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
