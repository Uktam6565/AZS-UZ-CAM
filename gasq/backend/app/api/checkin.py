from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.db.session import get_db
from app.models.queue import QueueTicket

router = APIRouter(prefix="/checkin", tags=["checkin"])


@router.post("/by-claim", response_model=dict)
async def checkin_by_claim(payload: dict, db: AsyncSession = Depends(get_db)):
    claim_code = str(payload.get("claim_code", "")).strip()
    if not claim_code:
        raise HTTPException(400, "claim_code required")

    res = await db.execute(
        select(QueueTicket).where(QueueTicket.claim_code == claim_code)
    )
    t = res.scalars().first()
    if not t:
        raise HTTPException(404, "ticket not found")

    # логика: check-in допустим, когда ticket вызван (called)
    if t.status not in ["called", "fueling"]:
        raise HTTPException(400, f"ticket status is {t.status}, cannot check-in")

    t.check_in_at = datetime.utcnow()
    await db.commit()

    return {
        "ok": True,
        "ticket_id": t.id,
        "ticket_no": t.ticket_no,
        "status": t.status,
        "check_in_at": t.check_in_at.isoformat(),
        "station_id": t.station_id,
    }