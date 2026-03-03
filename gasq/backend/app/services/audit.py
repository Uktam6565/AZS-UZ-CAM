from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


def _extract_user_fields(user: Any) -> Dict[str, Any]:
    """
    require_role() может вернуть ORM User или dict.
    Делаем универсально.
    """
    if user is None:
        return {"user_id": None, "username": None, "role": None}

    # dict case
    if isinstance(user, dict):
        return {
            "user_id": user.get("id") or user.get("user_id") or user.get("sub"),
            "username": user.get("username"),
            "role": user.get("role"),
        }

    # ORM case
    return {
        "user_id": getattr(user, "id", None),
        "username": getattr(user, "username", None),
        "role": getattr(user, "role", None),
    }


def _client_ip(request: Request) -> Optional[str]:
    # Если стоит proxy — часто прилетает X-Forwarded-For
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


async def audit(
    db: AsyncSession,
    request: Request,
    user: Any,
    action: str,
    station_id: int | None = None,
    ticket_id: int | None = None,
    meta: Dict[str, Any] | None = None,
) -> None:
    """
    Пишем аудит. Никогда не ломаем основной сценарий: если audit упал — молча игнорим.
    """
    try:
        u = _extract_user_fields(user)

        row = AuditLog(
            user_id=u["user_id"],
            username=u["username"],
            role=u["role"],
            action=action,
            station_id=station_id,
            ticket_id=ticket_id,
            ip=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            meta=meta or None,
        )
        db.add(row)
        await db.commit()
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
