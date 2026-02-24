from datetime import datetime, date, time, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from math import ceil
from app.services.eta import calc_eta_for_ticket
from app.models.notification import Notification

import secrets

from app.db.session import get_db
from app.models.queue import QueueTicket
from app.models.station import Station
from app.services.notify import notify_ticket_called
from app.services.sms import SmsService
from app.core.deps import require_role
from app.services.audit import audit
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/queue", tags=["queue"])


def _prefix_for_fuel(fuel_type: str) -> str:
    ft = (fuel_type or "").strip().lower()
    if ft == "diesel":
        return "D"
    if ft in ("lpg", "gas"):
        return "G"
    if ft in ("ev", "electric"):
        return "E"
    return "A"

def _mask_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    p = "".join(ch for ch in str(phone) if ch.isdigit() or ch == "+")
    if len(p) < 7:
        return "***"
    head = p[:6]
    tail = p[-4:]
    return f"{head}***{tail}"


async def _next_ticket_no(db: AsyncSession, station_id: int, fuel_type: str) -> str:
    prefix = _prefix_for_fuel(fuel_type)

    stmt = (
        select(QueueTicket.ticket_no)
        .where(
            QueueTicket.station_id == station_id,
            QueueTicket.ticket_no.ilike(f"{prefix}%"),
        )
        .order_by(desc(QueueTicket.id))
        .limit(1)
    )
    res = await db.execute(stmt)
    last = res.scalar_one_or_none()

    if not last:
        return f"{prefix}001"

    try:
        num = int(last[1:])
    except Exception:
        num = 0

    num += 1
    return f"{prefix}{num:03d}"


@router.post("/join", response_model=dict)
async def join_queue(
    request: Request,
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db),
):
    # простая валидация
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    missing = [k for k in ("station_id", "fuel_type") if k not in payload]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing field(s): {', '.join(missing)}")

    try:
        station_id = int(payload["station_id"])
    except Exception:
        raise HTTPException(status_code=400, detail="station_id must be an integer")

    fuel_type = str(payload["fuel_type"]).strip().lower()
    if not fuel_type:
        raise HTTPException(status_code=400, detail="fuel_type is required")

    # проверяем станцию
    station = await db.get(Station, station_id)
    if not station or not getattr(station, "is_active", False):
        raise HTTPException(status_code=404, detail="Station not found or inactive")

    # генерим номер талона
    ticket_no = await _next_ticket_no(db, station_id, fuel_type)

    claim_code = secrets.token_hex(4).upper()  # 8 символов, например: "A1B2C3D4"

    # создаём талон
    t = QueueTicket(
        station_id=station_id,
        fuel_type=fuel_type,
        ticket_no=ticket_no,
        status="waiting",
        driver_phone=(str(payload.get("driver_phone")).strip() if payload.get("driver_phone") else None),
        driver_user_id=(int(payload["driver_user_id"]) if payload.get("driver_user_id") is not None else None),
        source=str(payload.get("source", "app")).strip().lower(),
        created_at=datetime.utcnow(),
        claim_code=claim_code,
    )

    db.add(t)

    # 🔑 КЛЮЧЕВО: flush → забираем id/поля → commit
    await db.flush()

    ticket_id = t.id
    ticket_no_out = t.ticket_no
    status_out = t.status
    source_out = t.source

    await db.commit()

    # audit (join может быть без авторизации — user=None ок)
    try:
        await audit(
            db=db,
            request=request,
            user=None,
            action="queue.join",
            station_id=station_id,
            ticket_id=ticket_id,
            meta={"ticket_no": ticket_no_out, "fuel_type": fuel_type, "source": source_out},
        )
    except Exception:
        # аудит не должен ломать join
        pass

    return {
        "id": t.id,
        "ticket_no": t.ticket_no,
        "status": t.status,
        "claim_code": t.claim_code,
    }



@router.get("/panel", response_model=dict)
async def queue_panel(
    station_id: int = Query(...),
    fuel_type: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    station = await db.get(Station, station_id)
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")

    ft = fuel_type.strip().lower() if fuel_type else None

    # 1) BUSY = сколько талонов сейчас "занимают колонку"
    # (called + fueling)
    stmt_busy = select(func.count()).select_from(QueueTicket).where(
        QueueTicket.station_id == station_id,
        QueueTicket.status.in_(["called", "fueling"]),
    )
    if ft:
        stmt_busy = stmt_busy.where(QueueTicket.fuel_type == ft)

    pumps_busy = (await db.execute(stmt_busy)).scalar_one()
    pumps_total = int(getattr(station, "pumps_count", 1) or 1)
    pumps_free = max(pumps_total - pumps_busy, 0)
    can_call_next = pumps_free > 0

    # 2) NEXT ticket (первый waiting)
    stmt_next = select(QueueTicket).where(
        QueueTicket.station_id == station_id,
        QueueTicket.status == "waiting",
    )
    if ft:
        stmt_next = stmt_next.where(QueueTicket.fuel_type == ft)

    res_next = await db.execute(stmt_next.order_by(QueueTicket.created_at.asc()).limit(1))
    next_t = res_next.scalars().first()

    # 3) CALLED list (called + fueling)
    stmt_called = select(QueueTicket).where(
        QueueTicket.station_id == station_id,
        QueueTicket.status.in_(["called", "fueling"]),
    )
    if ft:
        stmt_called = stmt_called.where(QueueTicket.fuel_type == ft)

    res_called = await db.execute(stmt_called.order_by(QueueTicket.called_at.desc().nullslast()).limit(20))
    called_items = res_called.scalars().all()

    # 4) WAITING list
    stmt_waiting = select(QueueTicket).where(
        QueueTicket.station_id == station_id,
        QueueTicket.status == "waiting",
    )
    if ft:
        stmt_waiting = stmt_waiting.where(QueueTicket.fuel_type == ft)

    res_waiting = await db.execute(stmt_waiting.order_by(QueueTicket.created_at.asc()).limit(50))
    waiting_items = res_waiting.scalars().all()

    return {
        "station_id": station_id,
        "fuel_type": fuel_type,
        "pumps_total": pumps_total,
        "pumps_busy": pumps_busy,
        "pumps_free": pumps_free,
        "can_call_next": can_call_next,
        "next_ticket": (
            {
                "id": next_t.id,
                "ticket_no": next_t.ticket_no,
                "fuel_type": next_t.fuel_type,
                "created_at": next_t.created_at.isoformat(),
            }
            if next_t and can_call_next
            else None
        ),
        "called": [
            {
                "id": t.id,
                "ticket_no": t.ticket_no,
                "status": t.status,
                "called_at": t.called_at.isoformat() if t.called_at else None,
            }
            for t in called_items
        ],
        "waiting": [
            {
                "id": t.id,
                "ticket_no": t.ticket_no,
                "status": t.status,
                "created_at": t.created_at.isoformat(),
                "driver_phone_masked": _mask_phone(getattr(t, "driver_phone", None)),
            }
            for t in waiting_items
        ],
        "waiting_count": len(waiting_items),
    }

@router.post("/call-next", response_model=dict)
async def call_next_ticket(
    station_id: int = Query(..., description="ID станции"),
    db: AsyncSession = Depends(get_db),
):
    station = await db.get(Station, station_id)
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")

    pumps_total = int(getattr(station, "pumps_count", 1) or 1)

    # Сколько сейчас реально занято (fueling)
    stmt_busy = select(func.count()).select_from(QueueTicket).where(
        QueueTicket.station_id == station_id,
        QueueTicket.status == "fueling",
    )
    pumps_busy = int((await db.execute(stmt_busy)).scalar() or 0)

    if pumps_busy >= pumps_total:
        # 409 = конфликт состояния (нельзя вызывать)
        raise HTTPException(status_code=409, detail="All pumps are busy. Finish fueling first.")

    # Ищем первый waiting
    stmt = (
        select(QueueTicket)
        .where(
            QueueTicket.station_id == station_id,
            QueueTicket.status == "waiting",
        )
        .order_by(QueueTicket.created_at.asc())
        .limit(1)
    )
    res = await db.execute(stmt)
    t = res.scalars().first()

    if not t:
        raise HTTPException(status_code=404, detail="Очередь пуста")

    now = datetime.utcnow()
    t.status = "called"
    t.called_at = now

    note = Notification(
        station_id=t.station_id,
        ticket_id=t.id,
        type="operator_called",
        message=f"Талон {t.ticket_no}: подъезжайте к колонке",
    )
    db.add(note)

    await db.commit()
    await db.refresh(t)

    return {
        "ok": True,
        "station_id": station_id,
        "ticket_id": t.id,
        "ticket_no": t.ticket_no,
        "status": t.status,
        "called_at": t.called_at.isoformat() if t.called_at else None,
        "pumps_total": pumps_total,
        "pumps_busy": pumps_busy,
        "pumps_free": max(pumps_total - pumps_busy, 0),
    }

def _mask_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    p = "".join(ch for ch in str(phone) if ch.isdigit() or ch == "+")
    if len(p) < 7:
        return "***"
    # +998901234567 -> +99890***4567
    head = p[:6]
    tail = p[-4:]
    return f"{head}***{tail}"

def get_bearer_token(request: Request) -> str | None:
    auth = request.headers.get("Authorization")
    if not auth:
        return None
    prefix = "Bearer "
    if not auth.startswith(prefix):
        return None
    token = auth[len(prefix):].strip()
    return token or None

async def optional_user(request: Request):
    token = get_bearer_token(request)
    if token is None:
        return None

    try:
        payload = decode_token_payload(token)   # decode только если token есть
    except InvalidTokenError:  # или JWTError, depending on lib
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    # дальше — как у тебя принято: достаем user_id, грузим user из БД и т.д.
    return payload  # или user



@router.post("/check-in", response_model=dict)
async def check_in(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role not in ("admin", "operator"):
        raise HTTPException(status_code=403, detail="Forbidden")

    ticket_no = payload.get("ticket_no")
    claim_code = payload.get("claim_code")
    station_id = payload.get("station_id")

    if not ticket_no or not claim_code or not station_id:
        raise HTTPException(status_code=400, detail="Invalid payload")

    q = await db.execute(
        QueueTicket.__table__.select().where(
            QueueTicket.ticket_no == ticket_no,
            QueueTicket.station_id == station_id,
        )
    )
    ticket = q.first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ticket = ticket[0]

    if (ticket.claim_code or "").upper() != claim_code.upper():
        raise HTTPException(status_code=403, detail="Invalid claim_code")

    ticket.status = "called"
    await db.commit()
    await db.refresh(ticket)

    return {"ticket_no": ticket.ticket_no, "status": ticket.status}

@router.post("/set-status", response_model=dict)
async def set_ticket_status(
    request: Request,
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("admin", "operator")),
):
    # валидация
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    missing = [k for k in ("ticket_id", "status") if k not in payload]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing field(s): {', '.join(missing)}")

    try:
        ticket_id = int(payload["ticket_id"])
    except Exception:
        raise HTTPException(status_code=400, detail="ticket_id must be an integer")

    new_status = str(payload["status"]).strip().lower()

    allowed = {"waiting", "called", "fueling", "done", "cancelled"}
    if new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Allowed: {sorted(list(allowed))}",
        )

    # получаем талон
    t = await db.get(QueueTicket, ticket_id)
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")

    old_status = t.status

    # бизнес-логика
    t.status = new_status
    if new_status == "done":
        t.done_at = datetime.utcnow()

    # 🔑 flush → забрали значения → commit
    await db.flush()

    ticket_id_out = t.id
    ticket_no_out = t.ticket_no
    station_id_out = t.station_id
    status_out = t.status

    await db.commit()

    # audit — один, правильный, async-safe
    try:
        await audit(
            db=db,
            request=request,
            user=user,
            action="queue.set_status",
            station_id=station_id_out,
            ticket_id=ticket_id_out,
            meta={
                "ticket_no": ticket_no_out,
                "from": old_status,
                "to": status_out,
            },
        )
    except Exception:
        pass

    return {
        "ok": True,
        "id": ticket_id_out,
        "ticket_no": ticket_no_out,
        "status": status_out,
    }



@router.get("/stats", response_model=dict)
async def queue_stats(
    station_id: int = Query(...),
    fuel_type: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    station = await db.get(Station, station_id)
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")

    base_where = [QueueTicket.station_id == station_id]
    if fuel_type:
        base_where.append(QueueTicket.fuel_type == fuel_type.strip().lower())

    res_wait = await db.execute(
        select(func.count()).select_from(QueueTicket).where(*base_where, QueueTicket.status == "waiting")
    )
    waiting_count = int(res_wait.scalar() or 0)

    today = datetime.utcnow().date()
    res_done = await db.execute(
        select(func.count())
        .select_from(QueueTicket)
        .where(
            *base_where,
            QueueTicket.status == "done",
            QueueTicket.done_at.is_not(None),
            func.date(QueueTicket.done_at) == today,
        )
    )
    done_today = int(res_done.scalar() or 0)

    return {
        "station_id": station_id,
        "fuel_type": fuel_type,
        "waiting_count": waiting_count,
        "done_today": done_today,
    }


@router.get("/last-called", response_model=dict)
async def last_called(
    station_id: int,
    fuel_type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(QueueTicket).where(
        QueueTicket.station_id == station_id,
        QueueTicket.status == "called",
    )

    if fuel_type:
        stmt = stmt.where(QueueTicket.fuel_type == fuel_type)

    stmt = stmt.order_by(QueueTicket.called_at.desc()).limit(1)
    res = await db.execute(stmt)
    t = res.scalar_one_or_none()

    if not t:
        return {"ok": True, "ticket": None}

    return {"ok": True, "ticket": {"id": t.id, "ticket_no": t.ticket_no}}


@router.post("/start-fueling", response_model=dict)
async def start_fueling(
    ticket_id: int = Query(..., description="ID талона"),
    db: AsyncSession = Depends(get_db),
):
    t = await db.get(QueueTicket, ticket_id)
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if t.status != "called":
        raise HTTPException(status_code=400, detail=f"Cannot start fueling from status={t.status}")

    # 0) Станция и количество колонок
    station = await db.get(Station, t.station_id)
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")

    pumps_count = int(station.pumps_count or 1)

    # 1) Сколько сейчас уже обслуживаются (fueling)
    fueling_count = await db.scalar(
        select(func.count()).select_from(QueueTicket).where(
            QueueTicket.station_id == t.station_id,
            QueueTicket.status == "fueling",
        )
    )
    fueling_count = int(fueling_count or 0)

    if fueling_count >= pumps_count:
        raise HTTPException(
            status_code=409,
            detail=f"No free pumps: fueling={fueling_count}, pumps_count={pumps_count}",
        )

    now = datetime.utcnow()
    t.status = "fueling"

    note = Notification(
        station_id=t.station_id,
        ticket_id=t.id,
        type="fueling_started",
        message=f"Талон {t.ticket_no}: началось обслуживание",
    )
    db.add(note)

    await db.commit()
    await db.refresh(t)

    return {
        "ok": True,
        "ticket_id": t.id,
        "ticket_no": t.ticket_no,
        "status": t.status,
        "started_at": now.isoformat(),
    }


@router.post("/finish", response_model=dict)
async def finish_ticket(
    ticket_id: int = Query(..., description="ID талона"),
    db: AsyncSession = Depends(get_db),
):
    t = await db.get(QueueTicket, ticket_id)
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if t.status not in ("fueling", "called"):
        raise HTTPException(status_code=400, detail=f"Cannot finish from status={t.status}")

    now = datetime.utcnow()
    t.status = "done"
    t.done_at = now

    note = Notification(
        station_id=t.station_id,
        ticket_id=t.id,
        type="ticket_done",
        message=f"Талон {t.ticket_no}: обслуживание завершено",
    )
    db.add(note)

    await db.commit()
    await db.refresh(t)

    return {"ok": True, "ticket_id": t.id, "ticket_no": t.ticket_no, "status": t.status, "done_at": now.isoformat()}



@router.get("/ticket/{ticket_id}", response_model=dict)
async def get_ticket(
    ticket_id: int,
    claim_code: Optional[str] = Query(default=None),
    user: Optional[User] = Depends(optional_user),  # ВАЖНО: оставить один optional_user
    db: AsyncSession = Depends(get_db),
):
    t = await db.get(QueueTicket, ticket_id)
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # авторизованный пользователь — ок
    if user:
        allowed = True
    else:
        # гость — только по claim_code
        allowed = bool(claim_code) and (t.claim_code == claim_code)

    if not allowed:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return {
        "id": t.id,
        "station_id": t.station_id,
        "ticket_no": t.ticket_no,
        "fuel_type": t.fuel_type,
        "status": t.status,
        "claim_code": t.claim_code,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "called_at": t.called_at.isoformat() if t.called_at else None,
        "done_at": t.done_at.isoformat() if t.done_at else None,
        "driver_phone_masked": _mask_phone(getattr(t, "driver_phone", None)),
        "source": getattr(t, "source", None),
    }

from math import ceil
from sqlalchemy import select, func


@router.get("/ticket/{ticket_id}/eta", response_model=dict)
async def ticket_eta(
    ticket_id: int,
    claim_code: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    t = await db.get(QueueTicket, ticket_id)
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # доступ: либо claim_code, либо (позже) user
    if claim_code is None or (t.claim_code or "").upper() != claim_code.upper():
        raise HTTPException(status_code=403, detail="Invalid claim_code")

    st = await db.get(Station, t.station_id)
    if not st:
        raise HTTPException(status_code=404, detail="Station not found")

    # сколько "реально впереди": waiting + called (и тот же fuel_type)
    res = await db.execute(
        select(func.count())
        .select_from(QueueTicket)
        .where(
            QueueTicket.station_id == t.station_id,
            QueueTicket.fuel_type == t.fuel_type,
            QueueTicket.status.in_(["waiting", "called"]),
            QueueTicket.id < t.id,
        )
    )
    ahead = int(res.scalar() or 0)

    avg = int(getattr(st, "avg_service_min", 5) or 5)
    pumps = int(getattr(st, "pumps_count", 1) or 1)
    if pumps < 1:
        pumps = 1

    eta_min = await calc_eta_for_ticket(db, t)

    return {
        "ok": True,
        "ticket_id": t.id,
        "ticket_no": t.ticket_no,
        "waiting_ahead": None,  # можно убрать или оставить для совместимости
        "eta_min": eta_min,
    }

@router.post("/driver-state", response_model=dict)
async def set_driver_state(
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Водитель меняет состояние: idle / heading / arrived
    payload:
      - ticket_id: int
      - state: "idle" | "heading" | "arrived"
    """
    ticket_id = payload.get("ticket_id")
    state = (payload.get("state") or "").strip().lower()

    if not ticket_id or state not in ("idle", "heading", "arrived"):
        raise HTTPException(status_code=400, detail="Invalid payload (ticket_id, state)")

    t = await db.get(QueueTicket, int(ticket_id))
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")

    now = datetime.utcnow()
    t.driver_state = state

    if state == "heading":
        t.heading_at = now

        # Уведомление для операторской панели
        note = Notification(
            station_id=t.station_id,
            ticket_id=t.id,
            type="driver_heading",
            message=f"Талон {t.ticket_no}: водитель подъезжает",
            created_at=now,
        )
        db.add(note)

    if state == "arrived":
        t.arrived_at = now

        note = Notification(
            station_id=t.station_id,
            ticket_id=t.id,
            type="driver_arrived",
            message=f"Талон {t.ticket_no}: водитель прибыл",
            created_at=now,
        )
        db.add(note)

    await db.commit()

    return {"ok": True, "ticket_id": t.id, "ticket_no": t.ticket_no, "driver_state": t.driver_state}

@router.get("/history", response_model=dict)
async def history(
    station_id: int = Query(...),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    fuel_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("admin", "operator", "viewer")),
):
    today = datetime.utcnow().date()
    d_from = date_from or today
    d_to = date_to or today

    if d_to < d_from:
        d_from, d_to = d_to, d_from

    start_dt = datetime.combine(d_from, time.min)
    end_dt = datetime.combine(d_to + timedelta(days=1), time.min)

    stmt = select(QueueTicket).where(
        QueueTicket.station_id == station_id,
        QueueTicket.created_at >= start_dt,
        QueueTicket.created_at < end_dt,
    )

    if fuel_type:
        stmt = stmt.where(QueueTicket.fuel_type == fuel_type.strip().lower())

    if status:
        stmt = stmt.where(QueueTicket.status == status.strip().lower())

    stmt = stmt.order_by(QueueTicket.id.desc()).limit(limit)
    res = await db.execute(stmt)
    items = res.scalars().all()

    counts = {}
    for t in items:
        counts[t.status] = counts.get(t.status, 0) + 1

    return {
        "station_id": station_id,
        "date_from": d_from.isoformat(),
        "date_to": d_to.isoformat(),
        "fuel_type": fuel_type,
        "status": status,
        "limit": limit,
        "counts": counts,
        "items": [
            {
                "id": t.id,
                "ticket_no": t.ticket_no,
                "fuel_type": t.fuel_type,
                "status": t.status,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "called_at": t.called_at.isoformat() if t.called_at else None,
                "done_at": t.done_at.isoformat() if t.done_at else None,
                "driver_phone": getattr(t, "driver_phone", None),
                "source": getattr(t, "source", None),
            }
            for t in items
        ],
        "generated_at": datetime.utcnow().isoformat(),
    }

@router.get("/active", response_model=dict)
async def active_tickets(
    station_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    # called
    called_res = await db.execute(
        select(QueueTicket).where(
            QueueTicket.station_id == station_id,
            QueueTicket.status == "called",
        ).order_by(QueueTicket.called_at.asc().nulls_last(), QueueTicket.id.asc())
    )
    called = called_res.scalars().all()

    # fueling
    fueling_res = await db.execute(
        select(QueueTicket).where(
            QueueTicket.station_id == station_id,
            QueueTicket.status == "fueling",
        ).order_by(QueueTicket.id.asc())
    )
    fueling = fueling_res.scalars().all()

    return {
        "station_id": station_id,
        "called": [{"id": t.id, "ticket_no": t.ticket_no, "fuel_type": t.fuel_type} for t in called],
        "fueling": [{"id": t.id, "ticket_no": t.ticket_no, "fuel_type": t.fuel_type} for t in fueling],
    }