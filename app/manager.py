import asyncio
import secrets
import time
from typing import Dict, Optional


class ClientManager:
    def __init__(self):
        self._id_to_ws: Dict[str, object] = {}
        self._id_expiry: Dict[str, float] = {}  # tunnel_id -> expiry ts
        self._pending: Dict[str, asyncio.Future] = {}
        self.lock = asyncio.Lock()

    async def register_tunnel_id(self, tunnel_id: Optional[str] = None, ttl_seconds: int = 21600) -> str:
        if not tunnel_id:
            tunnel_id = secrets.token_urlsafe(6)
        async with self.lock:
            self._id_expiry[tunnel_id] = time.time() + ttl_seconds
        return tunnel_id

    async def add_client(self, tunnel_id: str, ws):
        async with self.lock:
            self._id_to_ws[tunnel_id] = ws
            if tunnel_id not in self._id_expiry:
                self._id_expiry[tunnel_id] = time.time() + 21600
            print(f"[CONNECTED] {tunnel_id}, Active={len(self._id_to_ws)}")

    async def remove_client(self, ws):
        async with self.lock:
            for tid, cws in list(self._id_to_ws.items()):
                if cws == ws:
                    self._id_to_ws.pop(tid, None)
                    print(f"[DISCONNECTED] {tid}, Active={len(self._id_to_ws)}")

    async def get_ws(self, tunnel_id: str):
        async with self.lock:
            # expire check
            exp = self._id_expiry.get(tunnel_id)
            if exp and exp < time.time():
                self._id_to_ws.pop(tunnel_id, None)
                self._id_expiry.pop(tunnel_id, None)
                return None
            return self._id_to_ws.get(tunnel_id)

    async def create_request_future(self, req_id: str) -> asyncio.Future:
        fut: asyncio.Future = asyncio.get_event_loop().create_future()
        async with self.lock:
            self._pending[req_id] = fut
        return fut

    async def resolve_request(self, req_id: str, payload: dict):
        async with self.lock:
            fut = self._pending.pop(req_id, None)
        if fut and not fut.done():
            fut.set_result(payload)


client_manager = ClientManager()
