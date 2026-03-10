from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.realtime import manager

router = APIRouter()


@router.websocket("/ws/queue/{station_id}")
async def websocket_queue(websocket: WebSocket, station_id: int):

    await manager.connect(station_id, websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(station_id, websocket)