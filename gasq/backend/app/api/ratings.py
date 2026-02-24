from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.rating import Rating
from app.models.station import Station

router = APIRouter(prefix="/ratings", tags=["ratings"])


@router.post("", response_model=dict)
async def create_rating(payload: dict, db: AsyncSession = Depends(get_db)):
    """
    Поставить оценку АЗС.
    payload:
      station_id (int) - обязательно
      stars (int 1..5) - обязательно
      title (str) - optional
      comment (str) - optional
      driver_user_id (int) - optional
    """
    for f in ["station_id", "stars"]:
        if f not in payload:
            raise HTTPException(status_code=400, detail=f"Missing field: {f}")

    station_id = int(payload["station_id"])
    station = await db.get(Station, station_id)
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")

    stars = int(payload["stars"])
    if stars < 1 or stars > 5:
        raise HTTPException(status_code=400, detail="stars must be 1..5")

    r = Rating(
        station_id=station_id,
        driver_user_id=payload.get("driver_user_id"),
        stars=stars,
        title=payload.get("title"),
        comment=payload.get("comment"),
    )
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return {"id": r.id}


@router.get("/by-station/{station_id}", response_model=list[dict])
async def list_ratings_by_station(
    station_id: int,
    limit: int = Query(default=20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    station = await db.get(Station, station_id)
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")

    res = await db.execute(
        select(Rating)
        .where(Rating.station_id == station_id)
        .order_by(Rating.id.desc())
        .limit(limit)
    )
    items = res.scalars().all()

    return [
        {
            "id": x.id,
            "stars": x.stars,
            "title": x.title,
            "comment": x.comment,
            "created_at": x.created_at.isoformat(),
        }
        for x in items
    ]


@router.get("/summary/{station_id}", response_model=dict)
async def rating_summary(station_id: int, db: AsyncSession = Depends(get_db)):
    station = await db.get(Station, station_id)
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")

    res = await db.execute(
        select(func.count(Rating.id), func.avg(Rating.stars)).where(Rating.station_id == station_id)
    )
    cnt, avg = res.one()
    return {"station_id": station_id, "count": int(cnt or 0), "avg": float(avg or 0.0)}
