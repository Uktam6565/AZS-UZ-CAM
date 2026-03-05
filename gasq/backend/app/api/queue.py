from datetime import datetime, date, time, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from math import ceil
from app.services.eta import calc_eta_for_ticket
from app.models.notification import Notification
from sqlalchemy.exc import IntegrityError

import secrets

from app.core.config import settings
from app.db.session import get_db
from app.models.queue import QueueTicket
from app.models.station import Station
from app.services.notify import notify_ticket_called
from app.services.sms import SmsService
from app.core.deps import require_role, get_current_user
from app.services.audit import audit
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

def _called_timer_info(t, now: datetime) -> dict:
    """
    Таймер ожидания после вызова (called_at).
    """
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

    # ----------------------------
    # v12: защита от дублей
    # ----------------------------
    active_statuses = ["waiting", "called", "fueling"]

    driver_user_id = None
    if payload.get("driver_user_id") is not None:
        try:
            driver_user_id = int(payload["driver_user_id"])
        except Exception:
            raise HTTPException(status_code=400, detail="driver_user_id must be integer")

    driver_phone = (str(payload.get("driver_phone")).strip() if payload.get("driver_phone") else None)

    # 1) По driver_user_id (если есть)
    if driver_user_id is not None:
        stmt_exist = (
            select(QueueTicket)
            .where(
                QueueTicket.station_id == station_id,
                QueueTicket.driver_user_id == driver_user_id,
                QueueTicket.status.in_(active_statuses),
            )
            .order_by(QueueTicket.id.desc())
            .limit(1)
        )
        res_exist = await db.execute(stmt_exist)
        exist = res_exist.scalars().first()
        if exist:
            return {
                "ok": True,
                "already_exists": True,
                "id": exist.id,
                "ticket_no": exist.ticket_no,
                "status": exist.status,
                "claim_code": exist.claim_code,
            }

    # 2) По driver_phone (если user_id нет, но есть телефон)
    if driver_user_id is None and driver_phone:
        stmt_exist = (
            select(QueueTicket)
            .where(
                QueueTicket.station_id == station_id,
                QueueTicket.driver_phone == driver_phone,
                QueueTicket.status.in_(active_statuses),
            )
            .order_by(QueueTicket.id.desc())
            .limit(1)
        )
        res_exist = await db.execute(stmt_exist)
        exist = res_exist.scalars().first()
        if exist:
            return {
                "ok": True,
                "already_exists": True,
                "id": exist.id,
                "ticket_no": exist.ticket_no,
                "status": exist.status,
                "claim_code": exist.claim_code,
            }

    # ----------------------------
    # создаём новый талон
    # ----------------------------

        # >>> v13: анти-спам join (cooldown)
        cooldown = int(getattr(settings, "JOIN_COOLDOWN_SECONDS", 0) or 0)

        if cooldown > 0:
            now = datetime.utcnow()

            # если есть user_id — проверяем по нему
            if driver_user_id is not None:
                stmt_last = (
                    select(QueueTicket)
                    .where(
                        QueueTicket.station_id == station_id,
                        QueueTicket.driver_user_id == driver_user_id,
                    )
                    .order_by(QueueTicket.id.desc())
                    .limit(1)
                )
                res_last = await db.execute(stmt_last)
                last = res_last.scalars().first()

                if last:
                    last_dt = getattr(last, "created_at", None) or now
                    age_sec = int((now - last_dt).total_seconds())
                    if age_sec < cooldown:
                        raise HTTPException(
                            status_code=429,
                            detail=f"Too many requests. Try again in {cooldown - age_sec}s",
                        )

            # если user_id нет, но есть телефон — проверяем по телефону
            elif driver_phone:
                stmt_last = (
                    select(QueueTicket)
                    .where(
                        QueueTicket.station_id == station_id,
                        QueueTicket.driver_phone == driver_phone,
                    )
                    .order_by(QueueTicket.id.desc())
                    .limit(1)
                )
                res_last = await db.execute(stmt_last)
                last = res_last.scalars().first()

                if last:
                    last_dt = getattr(last, "created_at", None) or now
                    age_sec = int((now - last_dt).total_seconds())
                    if age_sec < cooldown:
                        raise HTTPException(
                            status_code=429,
                            detail=f"Too many requests. Try again in {cooldown - age_sec}s",
                        )
    # <<< v13

    # генерим номер талона
    ticket_no = await _next_ticket_no(db, station_id, fuel_type)

    claim_code = secrets.token_hex(4).upper()  # 8 символов

    t = QueueTicket(
        station_id=station_id,
        fuel_type=fuel_type,
        ticket_no=ticket_no,
        status="waiting",
        driver_phone=driver_phone,
        driver_user_id=driver_user_id,
        source=str(payload.get("source", "app")).strip().lower(),
        created_at=datetime.utcnow(),
        claim_code=claim_code,
    )

    db.add(t)

    try:
        await db.flush()
        await db.commit()
    except IntegrityError:
        # Если одновременно прилетели два join — база могла зарубить уникальность
        await db.rollback()

        # 1) Сначала попробуем вернуть существующий активный талон (v12-логика)
        active_statuses = ["waiting", "called", "fueling"]

        if driver_user_id is not None:
            stmt = (
                select(QueueTicket)
                .where(
                    QueueTicket.station_id == station_id,
                    QueueTicket.driver_user_id == driver_user_id,
                    QueueTicket.status.in_(active_statuses),
                )
                .order_by(QueueTicket.id.desc())
                .limit(1)
            )
            res = await db.execute(stmt)
            exist = res.scalars().first()
            if exist:
                return {
                    "ok": True,
                    "already_exists": True,
                    "id": exist.id,
                    "ticket_no": exist.ticket_no,
                    "status": exist.status,
                    "claim_code": exist.claim_code,
                }

        if driver_user_id is None and driver_phone:
            stmt = (
                select(QueueTicket)
                .where(
                    QueueTicket.station_id == station_id,
                    QueueTicket.driver_phone == driver_phone,
                    QueueTicket.status.in_(active_statuses),
                )
                .order_by(QueueTicket.id.desc())
                .limit(1)
            )
            res = await db.execute(stmt)
            exist = res.scalars().first()
            if exist:
                return {
                    "ok": True,
                    "already_exists": True,
                    "id": exist.id,
                    "ticket_no": exist.ticket_no,
                    "status": exist.status,
                    "claim_code": exist.claim_code,
                }

        # 2) Если вдруг не нашли — пробуем создать новый талон повторно (очень редко)
        # Перегенерим ticket_no/claim_code и попробуем ещё раз
        ticket_no = await _next_ticket_no(db, station_id, fuel_type)
        claim_code = secrets.token_hex(4).upper()

        t = QueueTicket(
            station_id=station_id,
            fuel_type=fuel_type,
            ticket_no=ticket_no,
            status="waiting",
            driver_phone=driver_phone,
            driver_user_id=driver_user_id,
            source=str(payload.get("source", "app")).strip().lower(),
            created_at=datetime.utcnow(),
            claim_code=claim_code,
        )
        db.add(t)
        await db.flush()
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
        pass

    return {
        "ok": True,
        "already_exists": False,
        "id": t.id,
        "ticket_no": t.ticket_no,
        "status": t.status,
        "claim_code": t.claim_code,
    }



@router.get("/panel", response_model=dict)
async def panel(
    station_id: int = Query(...),
    fuel_type: str | None = Query(None, description="Filter waiting list by fuel_type"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("operator", "owner", "admin")),
):
    station = await db.get(Station, station_id)
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")

    pumps_total = int(getattr(station, "pumps_count", 1) or 1)
    ft = fuel_type.strip().lower() if fuel_type else None
    service_min = int(getattr(settings, "AVG_SERVICE_MINUTES", 5) or 5)

    # 1) Активные талоны на колонках (called/fueling)
    stmt_active = (
        select(QueueTicket)
        .where(
            QueueTicket.station_id == station_id,
            QueueTicket.status.in_(["called", "fueling"]),
        )
        .order_by(QueueTicket.pump_no.asc().nulls_last(), QueueTicket.called_at.asc().nulls_last())
    )
    res_active = await db.execute(stmt_active)
    active = res_active.scalars().all()

    active_by_pump: dict[int, dict] = {}
    for t in active:
        if t.pump_no:
            active_by_pump[int(t.pump_no)] = {
                "ticket_id": t.id,
                "ticket_no": t.ticket_no,
                "status": t.status,
                "fuel_type": t.fuel_type,
                "called_at": t.called_at.isoformat() if t.called_at else None,
                "check_in_at": t.check_in_at.isoformat() if t.check_in_at else None,
            }

    pumps = []
    for p in range(1, pumps_total + 1):
        pumps.append({"pump_no": p, "current": active_by_pump.get(p)})

    # 2) Waiting list
    conds = [
        QueueTicket.station_id == station_id,
        QueueTicket.status == "waiting",
    ]
    if ft:
        conds.append(QueueTicket.fuel_type == ft)

    stmt_waiting = (
        select(QueueTicket)
        .where(*conds)
        .order_by(QueueTicket.created_at.asc())
        .limit(200)
    )
    res_waiting = await db.execute(stmt_waiting)
    waiting = res_waiting.scalars().all()

    waiting_out = []
    for i, t in enumerate(waiting, start=1):
        cars_ahead = i - 1
        eta_min = ceil(cars_ahead / max(pumps_total, 1)) * service_min

        waiting_out.append(
            {
                "position": i,
                "cars_ahead": cars_ahead,
                "eta_min": eta_min,
                "ticket_id": t.id,
                "ticket_no": t.ticket_no,
                "fuel_type": t.fuel_type,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
        )

    # 3) Stats
    stmt_stats = (
        select(QueueTicket.status, func.count())
        .where(QueueTicket.station_id == station_id)
        .group_by(QueueTicket.status)
    )
    res_stats = await db.execute(stmt_stats)
    stats = {row[0]: int(row[1]) for row in res_stats.all()}

    stmt_ft = (
        select(QueueTicket.fuel_type, func.count())
        .where(
            QueueTicket.station_id == station_id,
            QueueTicket.status == "waiting",
        )
        .group_by(QueueTicket.fuel_type)
    )
    res_ft = await db.execute(stmt_ft)
    fuel_types = [{"fuel_type": r[0], "waiting": int(r[1])} for r in res_ft.all()]

    return {
        "fuel_filter": ft,
        "fuel_types": fuel_types,
        "station_id": station_id,
        "pumps_total": pumps_total,
        "pumps": pumps,
        "waiting": waiting_out,
        "stats": stats,
        "settings": {"no_show_minutes": int(settings.NO_SHOW_MINUTES)},

        }

async def auto_no_show_cleanup(station_id: int, db: AsyncSession) -> int:
    """
    Автоматически отменяет талоны, которые были вызваны (called),
    но водитель не начал обслуживание слишком долго.
    Возвращает сколько талонов отменили.

    Правило:
      - отменяем только если status == "called"
      - called_at есть и достаточно старый
      - check_in_at == None (если водитель уже check-in — НЕ отменяем)
    """
    now = datetime.utcnow()
    threshold = now - timedelta(minutes=int(settings.NO_SHOW_MINUTES))

    stmt = select(QueueTicket).where(
        QueueTicket.station_id == station_id,
        QueueTicket.status == "called",
        QueueTicket.called_at.is_not(None),
        QueueTicket.called_at < threshold,
        QueueTicket.check_in_at.is_(None),   # ключевая защита
    )

    res = await db.execute(stmt)
    tickets = res.scalars().all()

    for t in tickets:
        freed_pump = getattr(t, "pump_no", None)

        # отменяем
        t.status = "cancelled"
        if hasattr(t, "cancel_reason"):
            t.cancel_reason = "no_show"
        if hasattr(t, "cancelled_at"):
            t.cancelled_at = now

        # освобождаем колонку
        if hasattr(t, "pump_no"):
            t.pump_no = None

        db.add(
            Notification(
                station_id=t.station_id,
                ticket_id=t.id,
                type="ticket_cancelled",
                message=(
                    f"Талон {t.ticket_no}: отменён (no_show)"
                    + (f", колонка №{freed_pump} освобождена" if freed_pump else "")
                ),
            )
        )

    # ВАЖНО: commit НЕ здесь (его делает no_show_loop)
    return len(tickets)

@router.post("/call-next", response_model=dict)
async def call_next_ticket(
    station_id: int = Query(..., description="ID станции"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("operator", "owner", "admin")),
):
    """
    Оператор вызывает следующего водителя:
    - проверяем свободные колонки
    - берём первый waiting талон
    - ставим status=called, called_at=now, pump_no=свободная колонка
    - пишем Notification
    """

    station = await db.get(Station, station_id)
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")

    pumps_total = int(getattr(station, "pumps_count", 1) or 1)

    # какие колонки заняты
    stmt_busy = select(QueueTicket.pump_no).where(
        QueueTicket.station_id == station_id,
        QueueTicket.status.in_(["called", "fueling"]),
        QueueTicket.pump_no.is_not(None),
    )
    res_busy = await db.execute(stmt_busy)
    busy_pumps = {row[0] for row in res_busy.all() if row[0] is not None}

    all_pumps = set(range(1, pumps_total + 1))
    free_pumps = sorted(list(all_pumps - busy_pumps))

    if not free_pumps:
        raise HTTPException(status_code=409, detail="Нет свободных колонок")

    pump_no = free_pumps[0]

    stmt_next = (
        select(QueueTicket)
        .where(
            QueueTicket.station_id == station_id,
            QueueTicket.status == "waiting",
        )
        .order_by(QueueTicket.created_at.asc())
        .limit(1)
    )
    res = await db.execute(stmt_next)
    t = res.scalars().first()

    if not t:
        raise HTTPException(status_code=404, detail="Очередь пуста")

    now = datetime.utcnow()
    t.status = "called"
    t.called_at = now
    t.pump_no = pump_no

    note = Notification(
        station_id=t.station_id,
        ticket_id=t.id,
        type="operator_called",
        message=f"Талон {t.ticket_no}: подъезжайте к колонке №{pump_no}",
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
        "pump_no": t.pump_no,
        "called_at": t.called_at.isoformat() if t.called_at else None,
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

@router.post("/start-fueling", response_model=dict)
async def start_fueling(
    ticket_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("operator", "owner", "admin")),
):
    """
    Начать обслуживание:
    - called -> fueling
    """
    t = await db.get(QueueTicket, ticket_id)
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if t.status != "called":
        raise HTTPException(status_code=400, detail=f"Cannot start fueling from status={t.status}")

    now = datetime.utcnow()
    t.status = "fueling"
    # можно сохранить факт начала обслуживания (если хочешь) — пока без новых колонок

    note = Notification(
        station_id=t.station_id,
        ticket_id=t.id,
        type="ticket_fueling",
        message=f"Талон {t.ticket_no}: началось обслуживание (колонка №{t.pump_no})" if t.pump_no else f"Талон {t.ticket_no}: началось обслуживание",
    )
    db.add(note)

    await db.commit()
    await db.refresh(t)

    return {
        "ok": True,
        "ticket_id": t.id,
        "ticket_no": t.ticket_no,
        "status": t.status,
        "pump_no": t.pump_no,
    }

@router.post("/done", response_model=dict)
async def finish_ticket(
    ticket_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("operator", "owner", "admin")),
):
    """
    Завершить обслуживание:
    - fueling -> done
    Освобождаем колонку (pump_no = None)
    """
    t = await db.get(QueueTicket, ticket_id)
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if t.status != "fueling":
        raise HTTPException(status_code=400, detail=f"Cannot finish from status={t.status}")

    now = datetime.utcnow()
    t.status = "done"
    t.done_at = now

    released_pump = t.pump_no
    t.pump_no = None

    note = Notification(
        station_id=t.station_id,
        ticket_id=t.id,
        type="ticket_done",
        message=f"Талон {t.ticket_no}: обслуживание завершено" + (f", колонка №{released_pump} свободна" if released_pump else ""),
    )
    db.add(note)

    await db.commit()
    await db.refresh(t)

    return {
        "ok": True,
        "ticket_id": t.id,
        "ticket_no": t.ticket_no,
        "status": t.status,
        "done_at": t.done_at.isoformat() if t.done_at else None,
        "released_pump": released_pump,
    }

@router.post("/recall", response_model=dict)
async def recall_ticket(
    ticket_id: int = Query(..., description="ID талона"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("operator", "owner", "admin")),
):
    """
    Перевызов водителя на ту же колонку.
    Разрешено только если статус=called и есть pump_no.
    """
    t = await db.get(QueueTicket, ticket_id)
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if t.status != "called":
        raise HTTPException(status_code=400, detail=f"Cannot recall from status={t.status}")

    if not getattr(t, "pump_no", None):
        raise HTTPException(status_code=400, detail="Ticket has no pump_no")

    now = datetime.utcnow()
    # Статус не меняем, но можно обновить called_at как "последний вызов"
    t.called_at = now

    db.add(
        Notification(
            station_id=t.station_id,
            ticket_id=t.id,
            type="operator_recall",
            message=f"Талон {t.ticket_no}: повторный вызов к колонке №{t.pump_no}",
        )
    )

    await db.commit()
    await db.refresh(t)

    return {
        "ok": True,
        "ticket_id": t.id,
        "ticket_no": t.ticket_no,
        "status": t.status,
        "pump_no": t.pump_no,
        "called_at": t.called_at.isoformat() if t.called_at else None,
    }

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


@router.post("/finish", response_model=dict)
async def finish_ticket(
    ticket_id: int = Query(..., description="ID талона"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("operator", "owner", "admin")),
):
    t = await db.get(QueueTicket, ticket_id)
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if t.status not in ["called", "fueling"]:
        raise HTTPException(status_code=400, detail=f"Cannot finish from status={t.status}")

    now = datetime.utcnow()
    t.status = "done"
    t.done_at = now

    # освобождаем колонку
    finished_pump = t.pump_no
    t.pump_no = None

    note = Notification(
        station_id=t.station_id,
        ticket_id=t.id,
        type="ticket_done",
        message=f"Талон {t.ticket_no}: обслуживание завершено",
    )
    db.add(note)

    await db.commit()
    await db.refresh(t)

    return {
        "ok": True,
        "ticket_id": t.id,
        "ticket_no": t.ticket_no,
        "status": t.status,
        "freed_pump_no": finished_pump,
        "done_at": t.done_at.isoformat() if t.done_at else None,
    }

@router.post("/cancel", response_model=dict)
async def cancel_ticket(
    ticket_id: int = Query(..., description="ID талона"),
    reason: str = Query(default="driver", description="Причина: driver / other"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("operator", "owner", "admin")),
):
    """
    Отмена талона (обычно со стороны водителя):
    - waiting/called -> cancelled
    - если был called -> освобождаем колонку
    - пишем Notification
    """
    t = await db.get(QueueTicket, ticket_id)
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if t.status not in ("waiting", "called"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel from status={t.status}")

    old_pump = getattr(t, "pump_no", None)

    t.status = "cancelled"
    t.pump_no = None  # освобождаем колонку, если была назначена

    db.add(
        Notification(
            station_id=t.station_id,
            ticket_id=t.id,
            type="ticket_cancelled",
            message=f"Талон {t.ticket_no}: отменён ({reason})",
        )
    )

    await db.commit()
    await db.refresh(t)

    return {
        "ok": True,
        "ticket_id": t.id,
        "ticket_no": t.ticket_no,
        "status": t.status,
        "freed_pump_no": old_pump,
        "reason": reason,
    }

@router.post("/no-show", response_model=dict)
async def no_show(
    ticket_id: int = Query(..., description="ID талона"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("operator", "owner", "admin")),
):
    """
    Водитель не приехал после вызова:
    - разрешено только если status=called
    - если check_in_at уже есть -> запрещаем (чтобы не отменить после check-in)
    - status -> cancelled
    - cancel_reason = no_show (если поле есть)
    - cancelled_at = now (если поле есть)
    - освобождаем колонку (pump_no -> None)
    - пишем Notification
    """
    t = await db.get(QueueTicket, ticket_id)
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if t.status != "called":
        raise HTTPException(status_code=400, detail=f"Cannot no-show from status={t.status}")

    # защита: если уже check-in, то no-show запрещён
    if getattr(t, "check_in_at", None) is not None:
        raise HTTPException(status_code=400, detail="Cannot no-show after check-in")

    old_pump = getattr(t, "pump_no", None)
    now = datetime.utcnow()

    t.status = "cancelled"
    if hasattr(t, "cancel_reason"):
        t.cancel_reason = "no_show"
    if hasattr(t, "cancelled_at"):
        t.cancelled_at = now

    if hasattr(t, "pump_no"):
        t.pump_no = None

    db.add(
        Notification(
            station_id=t.station_id,
            ticket_id=t.id,
            type="ticket_cancelled",
            message=(
                f"Талон {t.ticket_no}: отменён (no_show)"
                + (f", колонка №{old_pump} освобождена" if old_pump else "")
            ),
        )
    )

    await db.commit()
    await db.refresh(t)

    return {
        "ok": True,
        "ticket_id": t.id,
        "ticket_no": t.ticket_no,
        "status": t.status,
        "freed_pump_no": old_pump,
        "cancel_reason": getattr(t, "cancel_reason", None),
        "cancelled_at": getattr(t, "cancelled_at", None).isoformat() if getattr(t, "cancelled_at", None) else None,
    }

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
   	    "called": [
                  {
                         "id": t.id,
           		 "ticket_no": t.ticket_no,
            		"fuel_type": t.fuel_type,
            		"claim_code": t.claim_code,
           	        "driver_phone": t.driver_phone,
        	  }
        	  for t in called
    	  ],
          "fueling": [
       	         {
                        "id": t.id,
            		"ticket_no": t.ticket_no,
            		"fuel_type": t.fuel_type,
            		"claim_code": t.claim_code,
            		"driver_phone": t.driver_phone,
                    "pump_no": t.pump_no,
        	}
        	for t in fueling
    	],
}

@router.get("/station/{station_id}/count")
async def queue_count(station_id: int, db: AsyncSession = Depends(get_db)):
    q = await db.execute(
        select(func.count())
        .select_from(QueueTicket)
        .where(
            QueueTicket.station_id == station_id,
            QueueTicket.status.in_(["waiting", "called", "fueling"])
        )
    )

    count = q.scalar() or 0

    return {
        "station_id": station_id,
        "queue": count
    }