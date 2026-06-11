"""
WebSocket Route — /ws/neural
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from visualization.ws_events import register_client, unregister_client, emit_event
from db.mongodb import get_db
import asyncio, json

router = APIRouter()

@router.websocket("/ws/neural")
async def neural_ws(ws: WebSocket):
    await ws.accept()
    await register_client(ws)

    try:
        # أرسل snapshot أولي
        db = get_db()
        cells = await db.cells.find(
            {"is_retired": False},
            {"_id": 0}
        ).to_list(100)

        await ws.send_text(json.dumps({
            "event": "SNAPSHOT",
            "data":  {"cells": cells},
        }))

        # استقبل رسائل (keep-alive)
        while True:
            try:
                msg = await asyncio.wait_for(ws.receive_text(), timeout=30)
                if msg == "ping":
                    await ws.send_text(json.dumps({"event": "PONG"}))
            except asyncio.TimeoutError:
                await ws.send_text(json.dumps({"event": "HEARTBEAT"}))

    except WebSocketDisconnect:
        await unregister_client(ws)
    except Exception:
        await unregister_client(ws)
