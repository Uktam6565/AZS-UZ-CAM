from math import radians, sin, cos, sqrt, atan2
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func

from app.core.config import settings
from app.db.session import get_db
from app.models.station import Station
from app.models.queue import QueueTicket

router = APIRouter(prefix="/stations", tags=["stations"])


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Расстояние по формуле гаверсинуса (км).
    Нужно для "ближайших АЗС" без PostGIS (MVP).
    """
    r = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return r * c


@router.post("", response_model=dict)
async def create_station(
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    Создание АЗС (для MVP — без авторизации, позже подключим JWT владельца).
    payload ожидает поля:
      name, address, latitude, longitude, fuel_types,
      has_cafe, has_shop, has_service, has_toilet, has_wifi, is_active
    """
    required = ["name", "address", "latitude", "longitude"]
    for f in required:
        if f not in payload:
            raise HTTPException(status_code=400, detail=f"Missing field: {f}")

    st = Station(
        owner_user_id=payload.get("owner_user_id"),
        name=str(payload["name"]).strip(),
        address=str(payload["address"]).strip(),
        description=payload.get("description"),
        latitude=float(payload["latitude"]),
        longitude=float(payload["longitude"]),
        fuel_types=payload.get("fuel_types", "gasoline,diesel"),

        avg_service_min=int(payload.get("avg_service_min", 5)),
        pumps_count=int(payload.get("pumps_count", 1)),

        has_cafe=bool(payload.get("has_cafe", False)),
        has_shop=bool(payload.get("has_shop", False)),
        has_service=bool(payload.get("has_service", False)),
        has_toilet=bool(payload.get("has_toilet", False)),
        has_wifi=bool(payload.get("has_wifi", False)),
        is_active=bool(payload.get("is_active", True)),
    )
    db.add(st)
    await db.commit()
    await db.refresh(st)
    return {"id": st.id}


@router.get("", response_model=list[dict])
async def list_stations(
    q: Optional[str] = Query(default=None, description="Поиск по названию"),
    fuel: Optional[str] = Query(default=None, description="Фильтр по топливу: gasoline/diesel/lpg/ev"),
    has_cafe: Optional[bool] = Query(default=None),
    has_shop: Optional[bool] = Query(default=None),
    has_service: Optional[bool] = Query(default=None),
    has_toilet: Optional[bool] = Query(default=None),
    has_wifi: Optional[bool] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Публичный список АЗС (для карты водителей + фильтры).
    """
    stmt = select(Station).where(Station.is_active == True)  # noqa: E712

    if q:
        stmt = stmt.where(Station.name.ilike(f"%{q.strip()}%"))

    if fuel:
        fuel = fuel.strip().lower()
        # fuel_types хранится строкой "gasoline,diesel,lpg"
        stmt = stmt.where(Station.fuel_types.ilike(f"%{fuel}%"))

    if has_cafe is not None:
        stmt = stmt.where(Station.has_cafe == has_cafe)
    if has_shop is not None:
        stmt = stmt.where(Station.has_shop == has_shop)
    if has_service is not None:
        stmt = stmt.where(Station.has_service == has_service)
    if has_toilet is not None:
        stmt = stmt.where(Station.has_toilet == has_toilet)
    if has_wifi is not None:
        stmt = stmt.where(Station.has_wifi == has_wifi)

    res = await db.execute(stmt)
    items = res.scalars().all()

    return [
        {
            "id": s.id,
            "name": s.name,
            "address": s.address,
            "latitude": s.latitude,
            "longitude": s.longitude,
            "fuel_types": s.fuel_types,
            "services": {
                "cafe": s.has_cafe,
                "shop": s.has_shop,
                "service": s.has_service,
                "toilet": s.has_toilet,
                "wifi": s.has_wifi,
            },
            "is_active": s.is_active,
        }
        for s in items
    ]

@router.get("/map", response_model=list[dict])
async def map_stations(
    bbox: str = Query(..., description="minLon,minLat,maxLon,maxLat"),
    fuel: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Станции в пределах текущего окна карты (bbox).
    MVP без PostGIS: фильтруем по latitude/longitude.
    """
    try:
        min_lon, min_lat, max_lon, max_lat = [float(x) for x in bbox.split(",")]
    except Exception:
        raise HTTPException(status_code=400, detail="bbox must be 'minLon,minLat,maxLon,maxLat'")

    stmt = select(Station).where(
        Station.is_active == True,  # noqa: E712
        Station.latitude >= min_lat,
        Station.latitude <= max_lat,
        Station.longitude >= min_lon,
        Station.longitude <= max_lon,
    )

    if fuel:
        fuel = fuel.strip().lower()
        stmt = stmt.where(Station.fuel_types.ilike(f"%{fuel}%"))

    res = await db.execute(stmt)
    items = res.scalars().all()

    return [
        {
            "id": s.id,
            "name": s.name,
            "latitude": s.latitude,
            "longitude": s.longitude,
            "fuel_types": s.fuel_types,
        }
        for s in items
    ]

from math import ceil

@router.get("/nearby", response_model=list[dict])
async def nearby_stations(
    lat: float = Query(..., description="Текущая широта пользователя"),
    lon: float = Query(..., description="Текущая долгота пользователя"),
    radius_km: float = Query(default=settings.DEFAULT_SEARCH_RADIUS_KM, ge=0.1, le=200.0),
    fuel: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    avg_speed_kmh: float = Query(default=35.0, ge=5.0, le=140.0),
    db: AsyncSession = Depends(get_db),
):
    """
    Ближайшие АЗС по GPS (MVP без PostGIS).
    + ETA дороги
    + ETA ожидания по очереди
    """
    stmt = select(Station).where(Station.is_active == True)  # noqa: E712
    if fuel:
        fuel = fuel.strip().lower()
        stmt = stmt.where(Station.fuel_types.ilike(f"%{fuel}%"))

    res = await db.execute(stmt)
    stations = res.scalars().all()

    out = []
    for s in stations:
        d = haversine_km(lat, lon, s.latitude, s.longitude)
        if d > radius_km:
            continue

        # ETA дороги
        eta_drive_min = max(1, int(round((d / avg_speed_kmh) * 60)))

        # Очередь: сколько WAITING сейчас на этой АЗС
        q_stmt = select(func.count()).select_from(QueueTicket).where(
            QueueTicket.station_id == s.id,
            QueueTicket.status == "waiting",
        )

        if fuel:
            q_stmt = q_stmt.where(QueueTicket.fuel_type == fuel)

        q_res = await db.execute(q_stmt)
        waiting_ahead = int(q_res.scalar() or 0)

        pumps = max(1, int(getattr(s, "pumps_count", 1) or 1))
        avg_service = max(1, int(getattr(s, "avg_service_min", 5) or 5))

        # ETA ожидания (мин)
        eta_queue_min = ceil(waiting_ahead / pumps) * avg_service
        eta_total_min = eta_drive_min + eta_queue_min

        out.append(
            {
                "id": s.id,
                "name": s.name,
                "address": s.address,
                "latitude": s.latitude,
                "longitude": s.longitude,
                "fuel_types": s.fuel_types,
                "avg_service_min": avg_service,
                "pumps_count": pumps,
                "distance_km": round(d, 3),
                "eta_drive_min": eta_drive_min,
                "waiting_ahead": waiting_ahead,
                "eta_queue_min": eta_queue_min,
                "eta_total_min": eta_total_min,
            }
        )

    out.sort(key=lambda x: x["eta_total_min"])
    return out[:limit]


@router.get("/{station_id}", response_model=dict)
async def get_station(station_id: int, db: AsyncSession = Depends(get_db)):
    st = await db.get(Station, station_id)
    if not st:
        raise HTTPException(status_code=404, detail="Station not found")
    return {
        "id": st.id,
        "name": st.name,
        "address": st.address,
        "description": st.description,
        "latitude": st.latitude,
        "longitude": st.longitude,
        "fuel_types": st.fuel_types,
        "services": {
            "cafe": st.has_cafe,
            "shop": st.has_shop,
            "service": st.has_service,
            "toilet": st.has_toilet,
            "wifi": st.has_wifi,
        },
        "is_active": st.is_active,
        "created_at": st.created_at.isoformat(),
        "updated_at": st.updated_at.isoformat(),
    }


@router.patch("/{station_id}", response_model=dict)
async def update_station(
    station_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    Обновление АЗС (админка). MVP: без авторизации, позже добавим JWT.
    """
    st = await db.get(Station, station_id)
    if not st:
        raise HTTPException(status_code=404, detail="Station not found")

    # обновляем только то, что передали
    for field in [
        "name",
        "address",
        "description",
        "latitude",
        "longitude",
        "fuel_types",
        "has_cafe",
        "has_shop",
        "has_service",
        "has_toilet",
        "has_wifi",
        "is_active",
    ]:
        if field in payload:
            setattr(st, field, payload[field])

    await db.commit()
    await db.refresh(st)
    return {"ok": True}
