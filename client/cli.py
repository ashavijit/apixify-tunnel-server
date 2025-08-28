import argparse
import asyncio
import json
import secrets
import time
from urllib.parse import urljoin

import httpx
import websockets


async def run_client(server: str, local_url: str, username: str | None, ttl: int):
    async with httpx.AsyncClient(base_url=server) as client:
        if username:
            r = await client.post("/register", json={"username": username, "ttl_seconds": ttl})
        else:
            r = await client.post("/random", json={"ttl_seconds": ttl})
        r.raise_for_status()
        data = r.json()
        tunnel_id = data["tunnel_id"]
        public_url = data["public_url"]
        print("Tunnel:", public_url)

    ws_url = server.replace("http", "ws") + "/ws"

    while True:
        try:
            async with websockets.connect(ws_url, max_size=16 * 1024 * 1024) as ws:
                await ws.send(json.dumps({"type": "register", "tunnel_id": tunnel_id}))
                print(f"[INFO] Connected to tunnel server. Listening for traffic...")

                async with httpx.AsyncClient(follow_redirects=True, timeout=20.0) as http:
                    while True:
                        try:
                            msg = await ws.recv()
                            data = json.loads(msg)
                            if data.get("type") != "request":
                                continue

                            p = data.get("payload")
                            rid = p.get("id")
                            path = p.get("path")
                            method = p.get("method")
                            headers = p.get("headers") or {}

                            for k in ["host", "connection", "transfer-encoding", "content-length"]:
                                headers.pop(k, None)

                            body = (p.get("body") or "").encode("utf-8")
                            query = p.get("query")

                            url = urljoin(local_url if local_url.endswith("/") else local_url + "/", path.lstrip("/"))
                            if query:
                                url = f"{url}?{query}"

                            resp = await http.request(method, url, headers=headers, content=body)

                            resp_headers = {
                                k: v for k, v in resp.headers.items()
                                if k.lower() not in {"transfer-encoding", "connection"}
                            }

                            await ws.send(json.dumps({
                                "type": "response",
                                "payload": {
                                    "id": rid,
                                    "status": resp.status_code,
                                    "headers": resp_headers,
                                    "body": resp.text,
                                },
                            }))
                        except Exception as e:
                            await ws.send(json.dumps({
                                "type": "response",
                                "payload": {
                                    "id": p.get("id", "unknown"),
                                    "status": 502,
                                    "headers": {"content-type": "text/plain"},
                                    "body": f"upstream error: {e}",
                                },
                            }))

        except websockets.exceptions.ConnectionClosedError as e:
            print(f"[WARN] WebSocket closed: {e}. Reconnecting in 5s...")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}. Reconnecting in 5s...")
            await asyncio.sleep(5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default="http://127.0.0.1:8000", help="Server base URL, e.g. http://host:8000")
    ap.add_argument("--port", type=int, required=True, help="Local port to expose")
    ap.add_argument("--username", default=None, help="Optional username to register")
    ap.add_argument("--ttl", type=int, default=21600, help="Session TTL seconds")
    args = ap.parse_args()
    local_url = f"http://127.0.0.1:{args.port}"
    asyncio.run(run_client(args.server, local_url, args.username, args.ttl))


if __name__ == "__main__":
    main()
