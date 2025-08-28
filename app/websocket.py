from fastapi import WebSocket
from .manager import client_manager
import json

async def websocket_handler(ws: WebSocket):
    await ws.accept()

    try:
        first = await ws.receive_text()
        data = json.loads(first)
        if data.get("type") != "register":
            await ws.close()
            return
        tunnel_id = data.get("tunnel_id")
        if not tunnel_id:
            await ws.close()
            return
    except Exception:
        await ws.close()
        return

    await client_manager.add_client(tunnel_id, ws)

    try:
        while True:
            text = await ws.receive_text()
            try:
                msg = json.loads(text)
            except Exception:
                continue
            if msg.get("type") == "response":
                payload = msg.get("payload") or {}
                req_id = payload.get("id")
                await client_manager.resolve_request(req_id, payload)
            else:
                pass
    except Exception:
        await client_manager.remove_client(ws)
