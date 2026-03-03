from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from app.services.eta import calc_eta_for_ticket
from fastapi.responses import StreamingResponse
import asyncio
import json
from fastapi import Request

from app.core.config import settings
from app.db.session import get_db
from app.models.queue import QueueTicket
from app.models.notification import Notification
from app.db.engine import AsyncSessionLocal

router = APIRouter(prefix="/driver", tags=["driver"])


def _called_timer_info(t: QueueTicket, now: datetime) -> dict:
    called_at = getattr(t, "called_at", None)
    if not called_at:
        return {
            "wait_called_sec": None,
            "wait_called_min": None,
            "no_show_after_min": int(getattr(settings, "NO_SHOW_MINUTES", 0) or 0),
            "no_show_left_min": None,
            "no_show_deadline_at": None,
        }

    no_show_min = int(getattr(settings, "NO_SHOW_MINUTES", 0) or 0)
    waited_sec = int((now - called_at).total_seconds())
    waited_min = max(waited_sec // 60, 0)

    deadline = called_at + timedelta(minutes=no_show_min) if no_show_min > 0 else None
    left_min = None
    if deadline:
        left_sec = int((deadline - now).total_seconds())
        left_min = max(left_sec // 60, 0)

    return {
        "wait_called_sec": max(waited_sec, 0),
        "wait_called_min": waited_min,
        "no_show_after_min": no_show_min,
        "no_show_left_min": left_min,
        "no_show_deadline_at": deadline.isoformat() if deadline else None,
    }

async def _build_ticket_snapshot(db: AsyncSession, t: QueueTicket) -> dict:
    now = datetime.utcnow()

    # position / cars_ahead
    stmt_pos = select(func.count()).where(
        QueueTicket.station_id == t.station_id,
        QueueTicket.status == "waiting",
        QueueTicket.created_at < t.created_at,
    )
    res_pos = await db.execute(stmt_pos)
    cars_ahead = int(res_pos.scalar() or 0)
    position = cars_ahead + 1

    # eta
    eta_min = None
    try:
        eta_min = await calc_eta_for_ticket(db, t)
    except Exception:
        eta_min = None

    return {
        "type": "ticket_snapshot",
        "ticket": {
            "id": t.id,
            "station_id": t.station_id,
            "ticket_no": t.ticket_no,
            "fuel_type": t.fuel_type,
            "status": t.status,
            "pump_no": t.pump_no,
            "position": position,
            "cars_ahead": cars_ahead,
            "eta_min": eta_min,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "called_at": t.called_at.isoformat() if t.called_at else None,
            "done_at": t.done_at.isoformat() if t.done_at else None,
            "cancelled_at": t.cancelled_at.isoformat() if t.cancelled_at else None,
            "cancel_reason": t.cancel_reason,
            "driver_state": t.driver_state,
            "heading_at": t.heading_at.isoformat() if t.heading_at else None,
            "arrived_at": t.arrived_at.isoformat() if t.arrived_at else None,
            "check_in_at": t.check_in_at.isoformat() if t.check_in_at else None,
            **_called_timer_info(t, now),
        },
    }

async def _get_ticket_by_claim(db: AsyncSession, claim_code: str) -> QueueTicket:
    code = (claim_code or "").strip().strip('"').strip("'").upper()
    if not code:
        raise HTTPException(status_code=400, detail="claim_code is required")

    stmt = select(QueueTicket).where(QueueTicket.claim_code == code).limit(1)
    res = await db.execute(stmt)
    t = res.scalars().first()
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return t


@router.get("/ticket", response_model=dict)
async def get_my_ticket(
    claim_code: str = Query(..., description="Secret claim code from /queue/join"),
    db: AsyncSession = Depends(get_db),
):
    t = await _get_ticket_by_claim(db, claim_code)
    now = datetime.utcnow()

    # --- position / cars_ahead ---
    stmt = select(func.count()).where(
        QueueTicket.station_id == t.station_id,
        QueueTicket.status == "waiting",
        QueueTicket.created_at < t.created_at,
        #QueueTicket.fuel_type == t.fuel_type
    )
    res = await db.execute(stmt)
    cars_ahead = int(res.scalar() or 0)
    position = cars_ahead + 1

    # --- ETA ---
    eta_min = None
    try:
        # если calc_eta_for_ticket async — оставь await
        eta_min = await calc_eta_for_ticket(db, t)
    except Exception:
        eta_min = None

    return {
        "id": t.id,
        "station_id": t.station_id,
        "ticket_no": t.ticket_no,
        "fuel_type": t.fuel_type,
        "status": t.status,
        "pump_no": t.pump_no,

        # 👇 НОВОЕ (Driver v2)
        "position": position,
        "cars_ahead": cars_ahead,
        "eta_min": eta_min,

        "created_at": t.created_at.isoformat() if t.created_at else None,
        "called_at": t.called_at.isoformat() if t.called_at else None,
        "done_at": t.done_at.isoformat() if t.done_at else None,
        "cancelled_at": t.cancelled_at.isoformat() if t.cancelled_at else None,
        "cancel_reason": t.cancel_reason,
        "driver_state": t.driver_state,
        "heading_at": t.heading_at.isoformat() if t.heading_at else None,
        "arrived_at": t.arrived_at.isoformat() if t.arrived_at else None,
        "check_in_at": t.check_in_at.isoformat() if t.check_in_at else None,
        **_called_timer_info(t, now),
    }


@router.post("/cancel", response_model=dict)
async def driver_cancel_ticket(
    claim_code: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    t = await _get_ticket_by_claim(db, claim_code)

    if t.status not in ("waiting", "called"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel from status={t.status}")

    now = datetime.utcnow()
    t.status = "cancelled"
    t.cancelled_at = now
    t.cancel_reason = "driver_cancel"

    db.add(Notification(
        station_id=t.station_id,
        ticket_id=t.id,
        type="ticket_cancelled",
        message=f"Талон {t.ticket_no}: отменён (driver)",
    ))

    await db.commit()
    await db.refresh(t)

    return {
        "ok": True,
        "ticket_id": t.id,
        "ticket_no": t.ticket_no,
        "status": t.status,
        "cancelled_at": t.cancelled_at.isoformat() if t.cancelled_at else None,
        "cancel_reason": t.cancel_reason,
    }


@router.post("/heading", response_model=dict)
async def driver_heading(
    claim_code: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    t = await _get_ticket_by_claim(db, claim_code)

    if t.status in ("done", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Cannot set heading from status={t.status}")

    now = datetime.utcnow()
    t.driver_state = "heading"
    t.heading_at = datetime.utcnow()
    note = Notification(
        station_id=t.station_id,
        ticket_id=t.id,
        type="driver_heading",
        message=f"Талон {t.ticket_no}: водитель выехал к АЗС",
    )
    db.add(note)

    await db.commit()
    await db.refresh(t)

    return {"ok": True, "driver_state": t.driver_state, "heading_at": t.heading_at.isoformat()}


@router.post("/arrived", response_model=dict)
async def driver_arrived(
    claim_code: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    t = await _get_ticket_by_claim(db, claim_code)

    if t.status in ("done", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Cannot set arrived from status={t.status}")

    now = datetime.utcnow()
    t.driver_state = "arrived"
    t.arrived_at = datetime.utcnow()
    note = Notification(
        station_id=t.station_id,
        ticket_id=t.id,
        type="driver_arrived",
        message=f"Талон {t.ticket_no}: водитель прибыл на АЗС",
    )
    db.add(note)

    await db.commit()
    await db.refresh(t)

    return {"ok": True, "driver_state": t.driver_state, "arrived_at": t.arrived_at.isoformat()}


@router.post("/check-in", response_model=dict)
async def driver_check_in(
    claim_code: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    t = await _get_ticket_by_claim(db, claim_code)

    if t.status not in ("called", "fueling"):
        raise HTTPException(status_code=400, detail=f"Cannot check-in from status={t.status}")

    now = datetime.utcnow()
    t.check_in_at = now
    note = Notification(
        station_id=t.station_id,
        ticket_id=t.id,
        type="driver_check_in",
        message=f"Талон {t.ticket_no}: водитель зарегистрировался (check-in)",
    )
    db.add(note)

    await db.commit()
    await db.refresh(t)

    return {"ok": True, "check_in_at": t.check_in_at.isoformat()}

@router.get("/events", response_class=StreamingResponse)
async def driver_events(
    request: Request,  # ← ВОТ СЮДА
    claim_code: str = Query(..., description="Secret claim code from /queue/join"),
):
    # 1) Один раз получаем ticket_id (короткая сессия)
    async with AsyncSessionLocal() as db:
        t = await _get_ticket_by_claim(db, claim_code)
        ticket_id = t.id
        station_id = t.station_id

    async def event_generator():
        last_id = 0

        # 2) Snapshot сразу при подключении (короткая сессия)
        try:
            async with AsyncSessionLocal() as db:
                t_db = await db.get(QueueTicket, ticket_id)
                if t_db:
                    snap = await _build_ticket_snapshot(db, t_db)
                    yield "data: " + json.dumps(snap, ensure_ascii=False) + "\n\n"

                stmt_last = select(func.max(Notification.id)).where(Notification.ticket_id == ticket_id)
                res_last = await db.execute(stmt_last)
                last_id = int(res_last.scalar() or 0)

        except Exception as e:
            yield "data: " + json.dumps({"type": "snapshot_error", "message": str(e)}, ensure_ascii=False) + "\n\n"

        # 3) Основной цикл — каждая итерация со своей сессией
        try:
            while True:
                # ✅ если клиент закрыл вкладку/Swagger остановил запрос — выходим
                if await request.is_disconnected():
                    return

                async with AsyncSessionLocal() as db:
                    stmt = (
                        select(Notification)
                        .where(
                            Notification.ticket_id == ticket_id,
                            Notification.id > last_id,
                        )
                        .order_by(Notification.id.asc())
                    )
                    res = await db.execute(stmt)
                    notes = res.scalars().all()

                    for n in notes:
                        last_id = n.id
                        payload = {
                            "type": n.type,
                            "message": n.message,
                            "created_at": n.created_at.isoformat() if getattr(n, "created_at", None) else None,
                            "ticket_id": n.ticket_id,
                            "station_id": n.station_id,
                        }
                        yield "data: " + json.dumps(payload, ensure_ascii=False) + "\n\n"

                        # v6: snapshot после каждого события
                        t_db = await db.get(QueueTicket, ticket_id)
                        if t_db:
                            snap = await _build_ticket_snapshot(db, t_db)
                            yield "data: " + json.dumps(snap, ensure_ascii=False) + "\n\n"

                # ping
                yield ": ping\n\n"

                # ✅ проверка ещё раз перед сном
                if await request.is_disconnected():
                    return

                await asyncio.sleep(10)

        except asyncio.CancelledError:
            return

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )