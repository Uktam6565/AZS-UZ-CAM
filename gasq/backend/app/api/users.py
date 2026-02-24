from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.core.security import hash_password
from app.core.deps import require_role

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


@router.get("", response_model=list[dict])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role("admin")),
):
    res = await db.execute(select(User).order_by(User.id.asc()))
    users = res.scalars().all()
    return [{"id": u.id, "username": u.username, "role": u.role} for u in users]


@router.post("", response_model=dict)
async def create_user(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role("admin")),
):
    """
    payload: { username, password, role }
    role: admin/operator/viewer
    """
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", "")).strip()
    role = str(payload.get("role", "viewer")).strip().lower()

    if not username or not password:
        raise HTTPException(status_code=400, detail="username and password required")

    if role not in ("admin", "operator", "viewer"):
        raise HTTPException(status_code=400, detail="invalid role")

    # uniqueness
    res = await db.execute(select(User).where(User.username == username))
    exists = res.scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=400, detail="username already exists")

    u = User(
        username=username,
        password_hash=hash_password(password),
        role=role,
        is_active=True,
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return {"ok": True, "id": u.id, "username": u.username, "role": u.role}


@router.patch("/{user_id}/role", response_model=dict)
async def set_role(
    user_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role("admin")),
):
    role = str(payload.get("role", "")).strip().lower()
    if role not in ("admin", "operator", "viewer"):
        raise HTTPException(status_code=400, detail="invalid role")

    u = await db.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="user not found")

    u.role = role
    await db.commit()
    return {"ok": True, "id": u.id, "role": u.role}


@router.patch("/{user_id}/password", response_model=dict)
async def set_password(
    user_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role("admin")),
):
    password = str(payload.get("password", "")).strip()
    if not password:
        raise HTTPException(status_code=400, detail="password required")

    u = await db.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="user not found")

    u.password_hash = hash_password(password)
    await db.commit()
    return {"ok": True, "id": u.id}


@router.delete("/{user_id}", response_model=dict)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role("admin")),
):
    u = await db.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="user not found")

    await db.delete(u)
    await db.commit()
    return {"ok": True}
