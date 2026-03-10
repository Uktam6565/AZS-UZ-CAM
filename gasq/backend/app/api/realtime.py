from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.db.session import AsyncSessionLocal
from app.services.queue_realtime import build_station_snapshot
from app.services.realtime_manager import realtime_manager

router = APIRouter(prefix="/realtime", tags=["realtime"])


@router.websocket("/queue/station/{station_id}")
async def queue_station_ws(websocket: WebSocket, station_id: int):
    await realtime_manager.connect_station(station_id, websocket)

    try:
        async with AsyncSessionLocal() as db:
            snapshot = await build_station_snapshot(db, station_id)

            await websocket.send_json(
                {
                    "event": "queue.snapshot",
                    "audience": "station",
                    "station_id": station_id,
                    "ticket_id": None,
                    "payload": {},
                    "snapshot": snapshot.model_dump(mode="json"),
                }
            )

        while True:
            msg = await websocket.receive_text()

            if msg == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        await realtime_manager.disconnect(websocket)
    except Exception:
        await realtime_manager.disconnect(websocket)


@router.websocket("/queue/ticket/{ticket_id}")
async def queue_ticket_ws(websocket: WebSocket, ticket_id: int):
    await realtime_manager.connect_driver(ticket_id, websocket)

    try:
        while True:
            msg = await websocket.receive_text()

            if msg == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        await realtime_manager.disconnect(websocket)
    except Exception:
        await realtime_manager.disconnect(websocket)