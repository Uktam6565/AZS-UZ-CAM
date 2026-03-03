import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.services.no_show_loop import no_show_loop

logger = logging.getLogger("gasq")

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.background_tasks = []

    task = asyncio.create_task(no_show_loop())
    app.state.background_tasks.append(task)
    logger.info("lifespan: started background tasks")

    try:
        yield
    finally:
        logger.info("lifespan: stopping background tasks...")
        for t in app.state.background_tasks:
            t.cancel()
        await asyncio.gather(*app.state.background_tasks, return_exceptions=True)
        logger.info("lifespan: background tasks stopped")