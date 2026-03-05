from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from uuid import uuid4

from app.db.session import get_db
from app.models.queue import QueueTicket
router = APIRouter(prefix="/operator", tags=["operator"])


@router.post("/call-next")
async def call_next(station_id: int, db: AsyncSession = Depends(get_db)):

    q = await db.execute(
        select(QueueTicket)
        .where(
            QueueTicket.station_id == station_id,
            QueueTicket.status == "waiting"
        )
        .order_by(QueueTicket.id.asc())
        .limit(1)
    )

    ticket = q.scalars().first()

    if not ticket:
        raise HTTPException(404, "no tickets")

    ticket.status = "called"
    ticket.called_at = datetime.utcnow()

    if not ticket.claim_code:
           ticket.claim_code = uuid4().hex[:10].upper()

    await db.commit()

    return {
        "ticket_no": ticket.ticket_no,
        "status": ticket.status
    }

@router.get("/waiting", response_model=dict)
async def waiting_list(station_id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(QueueTicket)
        .where(
            QueueTicket.station_id == station_id,
            QueueTicket.status == "waiting",
        )
        .order_by(QueueTicket.id.asc())
    )
    items = res.scalars().all()

    return {
        "station_id": station_id,
        "waiting": [
            {
                "id": t.id,
                "ticket_no": t.ticket_no,
                "fuel_type": t.fuel_type,
                "driver_phone": t.driver_phone,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in items
        ],
    }

@router.post("/start")
async def start_fueling(ticket_id: int, pump_no: int = 1, db: AsyncSession = Depends(get_db)):

    ticket = await db.get(QueueTicket, ticket_id)

    if not ticket:
        raise HTTPException(404, "ticket not found")

    ticket.status = "fueling"
    ticket.pump_no = pump_no

    await db.commit()

    return {
        "ticket_id": ticket.id,
        "status": ticket.status,
        "pump_no": ticket.pump_no
    }


@router.post("/done")
async def finish(ticket_id: int, db: AsyncSession = Depends(get_db)):

    ticket = await db.get(QueueTicket, ticket_id)

    if not ticket:
        raise HTTPException(404, "ticket not found")

    ticket.status = "done"
    ticket.done_at = datetime.utcnow()

    await db.commit()

    return {
        "ticket_id": ticket.id,
        "status": ticket.status
    }

@router.post("/call")
async def call_ticket(ticket_id: int, db: AsyncSession = Depends(get_db)):
    ticket = await db.get(QueueTicket, ticket_id)

    if not ticket:
        raise HTTPException(404, "ticket not found")

    if ticket.status != "waiting":
        raise HTTPException(400, "ticket is not waiting")

    ticket.status = "called"
    ticket.called_at = datetime.utcnow()

    await db.commit()

    return {
        "ticket_id": ticket.id,
        "ticket_no": ticket.ticket_no,
        "status": ticket.status
    }