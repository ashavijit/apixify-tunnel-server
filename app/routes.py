from fastapi import APIRouter, Request
from fastapi.responses import Response
from .manager import client_manager

router = APIRouter()

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(path: str, request: Request):
    ws = await client_manager.get_next_client()
    if not ws:
        return Response("No tunnels connected", status_code=502)

    body = await request.body()
    req_data = {
        "path": path,
        "method": request.method,
        "headers": dict(request.headers),
        "body": body.decode("utf-8", errors="ignore"),
    }

    await ws.send_json(req_data)

    try:
        data = await ws.receive_json()
        return Response(content=data["body"], status_code=data["status"])
    except Exception:
        return Response("Client error", status_code=500)
