import asyncio
import logging
from sqlalchemy import select

from app.db.engine import AsyncSessionLocal
from app.models import Station
from app.api.queue import auto_no_show_cleanup

logger = logging.getLogger("gasq")

async def no_show_loop():
    try:
        while True:
            try:
                async with AsyncSessionLocal() as db:
                    res = await db.execute(
                        select(Station.id).where(Station.is_active == True)
                    )
                    station_ids = [row[0] for row in res.all()]

                    total_cancelled = 0
                    for station_id in station_ids:
                        total_cancelled += await auto_no_show_cleanup(station_id, db)

                    await db.commit()

                    if total_cancelled:
                        logger.info(f"no_show_loop: auto-cancelled {total_cancelled} ticket(s)")

            except Exception:
                logger.exception("no_show_loop error")

            await asyncio.sleep(10)

    except asyncio.CancelledError:
        logger.info("no_show_loop cancelled")
        raise