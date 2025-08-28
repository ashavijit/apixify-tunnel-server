from fastapi import FastAPI, WebSocket
from .routes import router
from .websocket import websocket_handler

app = FastAPI(title="apix_bridge")

app.include_router(router)

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await websocket_handler(ws)
