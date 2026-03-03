from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.reservation import Reservation
from app.models.station import Station

router = APIRouter(prefix="/reservations", tags=["reservations"])


@router.post("", response_model=dict)
async def create_reservation(payload: dict, db: AsyncSession = Depends(get_db)):
    """
    Создать бронирование.
    payload:
      station_id (int) - обязательно
      fuel_type (str) - обязательно
      start_time (ISO datetime) - обязательно
      end_time (ISO datetime) - обязательно
      driver_phone (str) - optional
      driver_user_id (int) - optional
    """
    for f in ["station_id", "fuel_type", "start_time", "end_time"]:
        if f not in payload:
            raise HTTPException(status_code=400, detail=f"Missing field: {f}")

    station_id = int(payload["station_id"])
    station = await db.get(Station, station_id)
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")

    try:
        start_time = datetime.fromisoformat(str(payload["start_time"]))
        end_time = datetime.fromisoformat(str(payload["end_time"]))
    except Exception:
        raise HTTPException(status_code=400, detail="start_time/end_time must be ISO datetime")

    if end_time <= start_time:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")

    fuel_type = str(payload["fuel_type"]).strip().lower()

    # Проверка пересечений (MVP): нельзя бронировать пересекающееся время
    overlap_stmt = select(Reservation).where(
        Reservation.station_id == station_id,
        Reservation.status == "booked",
        and_(Reservation.start_time < end_time, Reservation.end_time > start_time),
    )
    overlap = (await db.execute(overlap_stmt)).scalars().first()
    if overlap:
        raise HTTPException(status_code=409, detail="Time slot is already booked")

    r = Reservation(
        station_id=station_id,
        fuel_type=fuel_type,
        start_time=start_time,
        end_time=end_time,
        driver_phone=payload.get("driver_phone"),
        driver_user_id=payload.get("driver_user_id"),
        status="booked",
    )
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return {"id": r.id, "status": r.status}


@router.get("/by-station/{station_id}", response_model=list[dict])
async def list_reservations_by_station(
    station_id: int,
    status: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    station = await db.get(Station, station_id)
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")

    stmt = select(Reservation).where(Reservation.station_id == station_id)
    if status:
        stmt = stmt.where(Reservation.status == status.strip().lower())

    res = await db.execute(stmt.order_by(Reservation.start_time.asc()).limit(200))
    items = res.scalars().all()

    return [
        {
            "id": x.id,
            "fuel_type": x.fuel_type,
            "start_time": x.start_time.isoformat(),
            "end_time": x.end_time.isoformat(),
            "status": x.status,
            "driver_phone": x.driver_phone,
        }
        for x in items
    ]


@router.post("/{reservation_id}/cancel", response_model=dict)
async def cancel_reservation(reservation_id: int, db: AsyncSession = Depends(get_db)):
    r = await db.get(Reservation, reservation_id)
    if not r:
        raise HTTPException(status_code=404, detail="Reservation not found")

    if r.status != "booked":
        return {"ok": True, "status": r.status}

    r.status = "cancelled"
    await db.commit()
    return {"ok": True, "status": r.status}
