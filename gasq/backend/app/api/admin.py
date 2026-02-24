from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User
from app.core.deps import require_role

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
)


@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("admin")),
):
    result = await db.execute(select(User))
    users = result.scalars().all()

    return [
        {
            "id": u.id,
            "username": u.username,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]
