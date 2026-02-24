from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User
from app.core.deps import require_role
from app.core.security import hash_password

router = APIRouter(
    prefix="/api/admin/users",
    tags=["admin"],
)


# 🔐 Только admin
admin_only = Depends(require_role("admin"))


@router.get("", dependencies=[admin_only])
async def list_users(db: AsyncSession = Depends(get_db)):
    """
    Получить список всех пользователей
    """
    res = await db.execute(select(User).order_by(User.id))
    users = res.scalars().all()

    return [
        {
            "id": u.id,
            "username": u.username,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at,
        }
        for u in users
    ]


@router.post("", dependencies=[admin_only])
async def create_user(
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    Создать нового пользователя
    payload:
      username (str)
      password (str)
      role (admin | operator | viewer)
    """
    username = payload.get("username")
    password = payload.get("password")
    role = payload.get("role", "viewer")

    if not username or not password:
        raise HTTPException(status_code=400, detail="username and password required")

    if role not in ("admin", "operator", "viewer"):
        raise HTTPException(status_code=400, detail="invalid role")

    exists = await db.execute(
        select(User).where(User.username == username)
    )
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="user already exists")

    user = User(
        username=username,
        password_hash=hash_password(password),
        role=role,
        is_active=True,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
    }


@router.patch("/{user_id}/role", dependencies=[admin_only])
async def change_role(
    user_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    Сменить роль пользователя
    payload:
      role (admin | operator | viewer)
    """
    role = payload.get("role")
    if role not in ("admin", "operator", "viewer"):
        raise HTTPException(status_code=400, detail="invalid role")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")

    user.role = role
    await db.commit()
    await db.refresh(user)

    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
    }
