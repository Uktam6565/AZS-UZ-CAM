from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import DefaultDict

from fastapi import WebSocket


class RealtimeConnectionManager:
    def __init__(self) -> None:
        self._station_connections: DefaultDict[int, set[WebSocket]] = defaultdict(set)
        self._driver_connections: DefaultDict[int, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect_station(self, station_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._station_connections[station_id].add(websocket)

    async def connect_driver(self, ticket_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._driver_connections[ticket_id].add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            for station_id in list(self._station_connections.keys()):
                if websocket in self._station_connections[station_id]:
                    self._station_connections[station_id].remove(websocket)
                if not self._station_connections[station_id]:
                    self._station_connections.pop(station_id, None)

            for ticket_id in list(self._driver_connections.keys()):
                if websocket in self._driver_connections[ticket_id]:
                    self._driver_connections[ticket_id].remove(websocket)
                if not self._driver_connections[ticket_id]:
                    self._driver_connections.pop(ticket_id, None)

    async def broadcast_station(self, station_id: int, message: dict) -> None:
        encoded = json.dumps(message, default=str)
        async with self._lock:
            targets = list(self._station_connections.get(station_id, set()))
        stale = []
        for ws in targets:
            try:
                await ws.send_text(encoded)
            except Exception:
                stale.append(ws)
        for ws in stale:
            await self.disconnect(ws)

    async def broadcast_driver(self, ticket_id: int, message: dict) -> None:
        encoded = json.dumps(message, default=str)
        async with self._lock:
            targets = list(self._driver_connections.get(ticket_id, set()))
        stale = []
        for ws in targets:
            try:
                await ws.send_text(encoded)
            except Exception:
                stale.append(ws)
        for ws in stale:
            await self.disconnect(ws)


realtime_manager = RealtimeConnectionManager()