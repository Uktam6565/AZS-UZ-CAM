from datetime import datetime, date, time, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_role
from app.db.session import get_db
from app.models.audit import AuditLog

router = APIRouter(prefix="/admin/audit", tags=["admin-audit"])


@router.get("", response_model=dict)
async def list_audit(
    request: Request,
    station_id: Optional[int] = Query(default=None),
    user_id: Optional[int] = Query(default=None),
    username: Optional[str] = Query(default=None),
    action: Optional[str] = Query(default=None),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("admin")),
):
    # по умолчанию: сегодня (UTC)
    today = datetime.utcnow().date()
    d_from = date_from or today
    d_to = date_to or today
    if d_to < d_from:
        d_from, d_to = d_to, d_from

    start_dt = datetime.combine(d_from, time.min)
    end_dt = datetime.combine(d_to + timedelta(days=1), time.min)

    stmt = select(AuditLog).where(
        AuditLog.created_at >= start_dt,
        AuditLog.created_at < end_dt,
    )

    if station_id is not None:
        stmt = stmt.where(AuditLog.station_id == station_id)
    if user_id is not None:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if username:
        stmt = stmt.where(AuditLog.username == username.strip())
    if action:
        stmt = stmt.where(AuditLog.action == action.strip())

    stmt = stmt.order_by(AuditLog.id.desc()).limit(limit)
    res = await db.execute(stmt)
    items = res.scalars().all()

    return {
        "date_from": d_from.isoformat(),
        "date_to": d_to.isoformat(),
        "limit": limit,
        "count": len(items),
        "items": [
            {
                "id": a.id,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "user_id": a.user_id,
                "username": a.username,
                "role": a.role,
                "action": a.action,
                "station_id": a.station_id,
                "ticket_id": a.ticket_id,
                "ip": a.ip,
                "user_agent": a.user_agent,
                "meta": a.meta,
            }
            for a in items
        ],
    }
