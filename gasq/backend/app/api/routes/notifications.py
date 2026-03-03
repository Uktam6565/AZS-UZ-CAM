from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession


from app.core.config import settings
from app.services.sms_eskiz import EskizSMS
from app.services.push_fcm import FCMService
from app.db.session import get_db
from app.models.notification import Notification

router = APIRouter(prefix="/notifications", tags=["notifications"])


class SMSRequest(BaseModel):
    phone: str
    message: str


class PushRequest(BaseModel):
    token: str
    title: str
    body: str
    data: dict | None = None

class ReadNotificationIn(BaseModel):
    notification_id: int = Field(..., ge=1)


class ReadAllNotificationsIn(BaseModel):
    station_id: int = Field(..., ge=1)


@router.post("/sms/test")
async def sms_test(payload: SMSRequest):
    if not settings.ESKIZ_EMAIL or not settings.ESKIZ_PASSWORD:
        raise HTTPException(status_code=400, detail="Eskiz credentials are not set")

    sms = EskizSMS(
        email=settings.ESKIZ_EMAIL,
        password=settings.ESKIZ_PASSWORD,
        sender=settings.ESKIZ_FROM or "4546",
    )
    res = await sms.send_sms(payload.phone, payload.message)
    return {"ok": True, "result": res}


@router.post("/push/test")
def push_test(payload: PushRequest):
    if not settings.FCM_SERVICE_ACCOUNT_PATH:
        raise HTTPException(status_code=400, detail="FCM_SERVICE_ACCOUNT_PATH is not set")

    fcm = FCMService(settings.FCM_SERVICE_ACCOUNT_PATH)
    msg_id = fcm.send_to_token(payload.token, payload.title, payload.body, payload.data)
    return {"ok": True, "message_id": msg_id}

@router.get("", response_model=list[dict])
async def list_notifications(
    station_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    In-app уведомления для оператора АЗС
    """
    res = await db.execute(
        select(Notification)
        .where(Notification.station_id == station_id)
        .order_by(Notification.created_at.desc())
        .limit(50)
    )
    items = res.scalars().all()

    return [
        {
            "id": n.id,
            "type": n.type,
            "message": n.message,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat(),
        }
        for n in items
    ]

@router.post("/read", response_model=dict)
async def mark_notification_read(
    payload: ReadNotificationIn,
    db: AsyncSession = Depends(get_db),
):
    note = await db.get(Notification, payload.notification_id)
    if not note:
        raise HTTPException(status_code=404, detail="Notification not found")

    if not note.is_read:
        note.is_read = True
        await db.commit()
        await db.refresh(note)

    return {"ok": True, "id": note.id, "is_read": note.is_read}


@router.post("/read-all", response_model=dict)
async def mark_all_notifications_read(
    payload: ReadAllNotificationsIn,
    db: AsyncSession = Depends(get_db),
):
    # Обновляем только те, что еще не прочитаны
    stmt = (
        update(Notification)
        .where(Notification.station_id == payload.station_id, Notification.is_read == False)  # noqa: E712
        .values(is_read=True)
        .execution_options(synchronize_session=False)
    )

    res = await db.execute(stmt)
    await db.commit()

    # rowcount = сколько строк реально обновилось
    marked = int(res.rowcount or 0)

    return {"ok": True, "station_id": payload.station_id, "marked_read": marked}


