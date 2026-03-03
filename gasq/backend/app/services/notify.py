from __future__ import annotations

from typing import Optional

from app.core.config import settings
from app.services.sms_eskiz import EskizSMS

try:
    from app.services.push_fcm import FCMService
except Exception:
    FCMService = None  # type: ignore


async def notify_ticket_called(
    *,
    station_name: str,
    ticket_no: str,
    driver_phone: Optional[str] = None,
    driver_push_token: Optional[str] = None,
) -> dict:
    """
    Sends notifications when ticket is called.
    Returns dict with delivery results.
    """
    result: dict = {"sms": None, "push": None}

    text = f"GasQ: Ваш талон {ticket_no} вызван на {station_name}. Подъезжайте к колонке."

    # --- SMS ---
    if settings.ENABLE_SMS_ON_CALL and driver_phone:
        if settings.ESKIZ_EMAIL and settings.ESKIZ_PASSWORD:
            sms = EskizSMS(
                email=settings.ESKIZ_EMAIL,
                password=settings.ESKIZ_PASSWORD,
                sender=settings.ESKIZ_FROM or "4546",
            )
            try:
                r = await sms.send_sms(driver_phone, text)
                result["sms"] = {"ok": True, "result": r}
            except Exception as e:
                result["sms"] = {"ok": False, "error": str(e)}
        else:
            result["sms"] = {"ok": False, "error": "Eskiz credentials not set"}
    else:
        result["sms"] = {"ok": False, "skipped": True}

    # --- PUSH ---
    if settings.ENABLE_PUSH_ON_CALL and driver_push_token:
        if settings.FCM_SERVICE_ACCOUNT_PATH and FCMService is not None:
            try:
                fcm = FCMService(settings.FCM_SERVICE_ACCOUNT_PATH)
                msg_id = fcm.send_to_token(
                    token=driver_push_token,
                    title="GasQ",
                    body=f"Ваш талон {ticket_no} вызван. Подъезжайте.",
                    data={"ticket_no": ticket_no, "station": station_name},
                )
                result["push"] = {"ok": True, "message_id": msg_id}
            except Exception as e:
                result["push"] = {"ok": False, "error": str(e)}
        else:
            result["push"] = {"ok": False, "error": "FCM not configured"}
    else:
        result["push"] = {"ok": False, "skipped": True}

    return result
