from fastapi import APIRouter, Request
from fastapi.responses import Response
from .manager import client_manager
import json
import secrets
import asyncio

router = APIRouter()


@router.post("/register")
async def register(payload: dict):
    username = (payload.get("username") or "").strip().lower() or None
    ttl = int(payload.get("ttl_seconds") or 21600)
    tunnel_id = await client_manager.register_tunnel_id(username, ttl_seconds=ttl) if username else await client_manager.register_tunnel_id(ttl_seconds=ttl)
    return {"tunnel_id": tunnel_id, "public_url": f"/{tunnel_id}"}


@router.post("/random")
async def random_register(payload: dict):
    ttl = int(payload.get("ttl_seconds") or 21600)
    tunnel_id = await client_manager.register_tunnel_id(ttl_seconds=ttl)
    return {"tunnel_id": tunnel_id, "public_url": f"/{tunnel_id}"}


@router.api_route("/{tunnel_id}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def proxy_tunnel(tunnel_id: str, path: str, request: Request):
    ws = await client_manager.get_ws(tunnel_id)
    if not ws:
        return Response("Tunnel not connected", status_code=502)

    body = await request.body()
    query = request.url.query
    req_id = secrets.token_hex(8)
    fut = await client_manager.create_request_future(req_id)
    print(f"[REQ] {req_id} -> {tunnel_id} {request.method} /{path}?{query}")
    req_data = {
        "type": "request",
        "payload": {
            "id": req_id,
            "path": "/" + path if not path.startswith("/") else path,
            "method": request.method,
            "headers": dict(request.headers),
            "body": body.decode("utf-8", errors="ignore"),
            "query": query,
        },
    }

    await ws.send_text(json.dumps(req_data))

    try:
        resp = await asyncio.wait_for(fut, timeout=60)
        body = resp.get("body", "")
        headers = resp.get("headers") or {}
        ctype_value = headers.get("content-type") or headers.get("Content-Type")
        ctype = (ctype_value or "").lower()
        if "text/html" in ctype and "openapi.json" in body and (path == "docs" or path.endswith("/docs")):
            body = body.replace('"/openapi.json"', f'"/{tunnel_id}/openapi.json"')
            body = body.replace("'/openapi.json'", f"'/{tunnel_id}/openapi.json'")
        status_code = int(resp.get("status", 200))
        print(f"[RES] {req_id} <- {tunnel_id} {status_code} bytes={len(body)}")
        return Response(content=body, status_code=status_code, media_type=ctype_value)
    except Exception:
        print(f"[ERR] {req_id} timeout/error")
        return Response("Client error or timeout", status_code=504)


@router.api_route("/{tunnel_id}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def proxy_tunnel_root(tunnel_id: str, request: Request):
    return await proxy_tunnel(tunnel_id, path="", request=request)
