"""
WebSocket Events — أحداث حية للـ Frontend
"""
import json
from datetime import datetime
from typing import Any

# Connected WebSocket clients
_clients: list = []

async def register_client(ws):
    _clients.append(ws)

async def unregister_client(ws):
    if ws in _clients:
        _clients.remove(ws)

async def emit_event(event_type: str, data: dict = None):
    """
    أحداث:
    CELL_CREATED / CELL_SPECIALIZED / CELL_RETIRED
    KNOWLEDGE_ADDED / CONNECTION_CREATED
    DISCOVERY_MADE / CONFIDENCE_UPDATED
    """
    payload = json.dumps({
        "event":     event_type,
        "data":      data or {},
        "timestamp": datetime.utcnow().isoformat(),
    })

    dead = []
    for ws in _clients:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.append(ws)

    for ws in dead:
        _clients.remove(ws)

def get_active_clients() -> int:
    return len(_clients)
