from fastapi import APIRouter, Query
from fastapi.responses import Response
import qrcode
from qrcode.constants import ERROR_CORRECT_M

router = APIRouter(prefix="/qr", tags=["qr"])


@router.get("/driver", response_class=Response)
def qr_driver(
    station_id: int = Query(..., ge=1),
    fuel_type: str | None = Query(default=None),
    frontend_base: str = Query(default="http://localhost:5500"),
):
    """
    Возвращает PNG QR-код для ссылки на driver/index.html.

    Пример:
    /api/qr/driver?station_id=1&fuel_type=gasoline
    """

    ft = (fuel_type or "").strip()
    link = f"{frontend_base.rstrip('/')}/driver/index.html?station_id={station_id}"
    if ft:
        link += f"&fuel_type={ft}"

    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(link)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # в bytes (PNG)
    import io
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    png = buf.getvalue()

    return Response(content=png, media_type="image/png")

