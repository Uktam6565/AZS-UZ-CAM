from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.pump import Pump
from app.models.station import Station
from app.core.deps import require_role

router = APIRouter(prefix="/pumps", tags=["pumps"])


@router.post("", response_model=dict)
async def create_pump(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("admin", "operator")),
):
    """
    Создание колонки/зарядки (админка).
    payload:
      station_id (int), name (str), fuel_type (gasoline/diesel/lpg/ev), price (float)
      is_active (bool, optional)
    """
    for f in ["station_id", "name", "fuel_type", "price"]:
        if f not in payload:
            raise HTTPException(status_code=400, detail=f"Missing field: {f}")

    station = await db.get(Station, int(payload["station_id"]))
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")

    pump = Pump(
        station_id=station.id,
        name=str(payload["name"]).strip(),
        fuel_type=str(payload["fuel_type"]).strip().lower(),
        price=float(payload["price"]),
        is_active=bool(payload.get("is_active", True)),
        is_busy=bool(payload.get("is_busy", False)),
        last_status_change=datetime.utcnow(),
    )
    db.add(pump)
    await db.commit()
    await db.refresh(pump)
    return {"id": pump.id}


@router.get("/by-station/{station_id}", response_model=list[dict])
async def list_pumps_by_station(station_id: int, db: AsyncSession = Depends(get_db)):
    """
    Публично: список колонок АЗС (для табло и приложения).
    """
    station = await db.get(Station, station_id)
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")

    res = await db.execute(select(Pump).where(Pump.station_id == station_id))
    pumps = res.scalars().all()

    return [
        {
            "id": p.id,
            "station_id": p.station_id,
            "name": p.name,
            "fuel_type": p.fuel_type,
            "price": p.price,
            "is_active": p.is_active,
            "is_busy": p.is_busy,
            "last_status_change": p.last_status_change.isoformat(),
        }
        for p in pumps
    ]


@router.patch("/{pump_id}", response_model=dict)
async def update_pump(
    pump_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("admin", "operator")),
):

    """
    Обновление колонки (админка):
      name, fuel_type, price, is_active
    """
    pump = await db.get(Pump, pump_id)
    if not pump:
        raise HTTPException(status_code=404, detail="Pump not found")

    for field in ["name", "fuel_type", "price", "is_active"]:
        if field in payload:
            setattr(pump, field, payload[field])

    await db.commit()
    await db.refresh(pump)
    return {"ok": True}


@router.post("/{pump_id}/set-busy", response_model=dict)
async def set_pump_busy(pump_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    """
    Быстрое переключение статуса свободно/занята (табло/оператор):
    payload: { "is_busy": true/false }
    """
    if "is_busy" not in payload:
        raise HTTPException(status_code=400, detail="Missing field: is_busy")

    pump = await db.get(Pump, pump_id)
    if not pump:
        raise HTTPException(status_code=404, detail="Pump not found")

    new_busy = bool(payload["is_busy"])
    if pump.is_busy != new_busy:
        pump.is_busy = new_busy
        pump.last_status_change = datetime.utcnow()

    await db.commit()
    return {"ok": True, "is_busy": pump.is_busy}


@router.post("/{pump_id}/set-price", response_model=dict)
async def set_pump_price(pump_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    """
    Обновление цены в реальном времени:
    payload: { "price": 12345.0 }
    """
    if "price" not in payload:
        raise HTTPException(status_code=400, detail="Missing field: price")

    pump = await db.get(Pump, pump_id)
    if not pump:
        raise HTTPException(status_code=404, detail="Pump not found")

    pump.price = float(payload["price"])
    await db.commit()
    return {"ok": True, "price": pump.price}


@router.delete("/{pump_id}", response_model=dict)
async def delete_pump(
    pump_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("admin")),
):

    """
    Удаление колонки (админка).
    """
    pump = await db.get(Pump, pump_id)
    if not pump:
        raise HTTPException(status_code=404, detail="Pump not found")

    await db.delete(pump)
    await db.commit()
    return {"ok": True}
