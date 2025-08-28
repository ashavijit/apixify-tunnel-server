import itertools
import asyncio

class ClientManager:
    def __init__(self):
        self.clients = []
        self.lock = asyncio.Lock()
        self.rr_cycle = None

    async def add_client(self, ws):
        async with self.lock:
            self.clients.append(ws)
            self.rr_cycle = itertools.cycle(self.clients)
            print(f"[CONNECTED] Clients={len(self.clients)}")

    async def remove_client(self, ws):
        async with self.lock:
            if ws in self.clients:
                self.clients.remove(ws)
            self.rr_cycle = itertools.cycle(self.clients) if self.clients else None
            print(f"[DISCONNECTED] Clients={len(self.clients)}")

    async def get_next_client(self):
        async with self.lock:
            if not self.clients:
                return None
            return next(self.rr_cycle)

client_manager = ClientManager()
