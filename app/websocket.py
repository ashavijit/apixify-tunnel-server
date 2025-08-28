from fastapi import WebSocket
from .manager import client_manager

async def websocket_handler(ws: WebSocket):
    await ws.accept()
    await client_manager.add_client(ws)

    try:
        while True:
            await ws.receive_text()  # keep alive
    except Exception:
        await client_manager.remove_client(ws)
