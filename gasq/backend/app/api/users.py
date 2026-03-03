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
    return [
        {
            "id": u.id,
            "phone": u.phone,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


@router.post("", response_model=dict)
async def create_user(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role("admin")),
):
    """
    payload: { phone, password, role }
    role: driver/operator/owner/admin
    """
    phone = str(payload.get("phone", "")).strip()
    password = str(payload.get("password", "")).strip()
    role = str(payload.get("role", "driver")).strip().lower()

    if not phone or not password:
        raise HTTPException(status_code=400, detail="phone and password required")

    if role not in ("driver", "operator", "owner", "admin"):
        raise HTTPException(status_code=400, detail="invalid role")

    res = await db.execute(select(User).where(User.phone == phone))
    exists = res.scalars().first()
    if exists:
        raise HTTPException(status_code=400, detail="phone already exists")

    u = User(
        phone=phone,
        password_hash=hash_password(password),
        role=role,
        is_active=True,
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)

    return {"ok": True, "id": u.id, "phone": u.phone, "role": u.role}


@router.patch("/{user_id}/role", response_model=dict)
async def set_role(
    user_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role("admin")),
):
    role = str(payload.get("role", "")).strip().lower()
    if role not in ("driver", "operator", "owner", "admin"):
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