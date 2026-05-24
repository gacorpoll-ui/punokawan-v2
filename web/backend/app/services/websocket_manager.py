"""WebSocket connection manager for real-time signal broadcasting."""

import asyncio
import json
from datetime import datetime
from typing import Any

from fastapi import WebSocket


class WSManager:
    """Manages WebSocket connections and broadcasts signals."""

    def __init__(self):
        self.active: list[WebSocket] = []
        self._last_signal: dict = {}

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)
        # Send last known signal on connect
        if self._last_signal:
            await ws.send_json(self._last_signal)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: dict):
        """Broadcast data to all connected clients."""
        self._last_signal = data
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    @property
    def connection_count(self) -> int:
        return len(self.active)


ws_manager = WSManager()
