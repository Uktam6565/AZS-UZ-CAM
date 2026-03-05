from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status

from app.core.security import decode_token_payload
from app.db.session import get_db
from app.models.user import User
from app.core.security import hash_password, verify_password, create_access_token
from app.api.deps import oauth2_scheme

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=dict)
async def register(payload: dict, db: AsyncSession = Depends(get_db)):
    phone = str(payload.get("phone", "")).strip()
    password = str(payload.get("password", "")).strip()
    role = str(payload.get("role", "driver")).strip()

    if not phone or not password:
        raise HTTPException(status_code=400, detail="phone and password required")

    if role not in ["driver", "operator", "owner", "admin"]:
        raise HTTPException(status_code=400, detail="invalid role")

    q = await db.execute(select(User).where(User.phone == phone))
    if q.scalars().first():
        raise HTTPException(status_code=409, detail="user already exists")

    u = User(phone=phone, password_hash=hash_password(password), role=role, is_active=True)
    db.add(u)
    await db.commit()
    await db.refresh(u)

    return {"ok": True, "id": u.id, "phone": u.phone, "role": u.role}


@router.post("/login", response_model=dict)
async def login(payload: dict, db: AsyncSession = Depends(get_db)):
    phone = str(payload.get("phone", "")).strip()
    password = str(payload.get("password", "")).strip()

    if not phone or not password:
        raise HTTPException(status_code=400, detail="phone and password required")

    q = await db.execute(select(User).where(User.phone == phone))
    u = q.scalars().first()
    if not u or not verify_password(password, u.password_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")

    token = create_access_token({"sub": str(u.id), "role": u.role})
    return {"access_token": token, "token_type": "bearer", "user": {"id": u.id, "role": u.role}}


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    payload = decode_token_payload(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    try:
        user_id = int(sub)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
        )

    return user

async def optional_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    if not token:
        return None
    try:
        return await get_current_user(token=token, db=db)
    except HTTPException:
        return None


