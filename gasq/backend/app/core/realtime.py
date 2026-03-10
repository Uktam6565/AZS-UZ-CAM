from fastapi import WebSocket
from typing import Dict, List


class ConnectionManager:
    def __init__(self):
        self.station_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, station_id: int, websocket: WebSocket):
        await websocket.accept()

        if station_id not in self.station_connections:
            self.station_connections[station_id] = []

        self.station_connections[station_id].append(websocket)

    def disconnect(self, station_id: int, websocket: WebSocket):
        if station_id in self.station_connections:
            if websocket in self.station_connections[station_id]:
                self.station_connections[station_id].remove(websocket)

    async def broadcast(self, station_id: int, message: dict):
        if station_id not in self.station_connections:
            return

        dead = []

        for ws in self.station_connections[station_id]:
            try:
                await ws.send_json(message)
            except:
                dead.append(ws)

        for ws in dead:
            self.station_connections[station_id].remove(ws)


manager = ConnectionManager()