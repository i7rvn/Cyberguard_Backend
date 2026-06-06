"""Dashboard Routes + WebSocket"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from db.schemas import ok, err
from db.mongodb import get_db
from systems.circuit_breaker import circuit_breaker
from systems.cache import result_cache
from datetime import datetime, timedelta
import asyncio, psutil, json

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/health")
async def health_score(request: Request):
    db = get_db()
    mem = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.1)

    # احسب System Health Score (0-100)
    scores = {}
    scores["memory"]  = max(0, 100 - mem.percent)
    scores["cpu"]     = max(0, 100 - cpu)
    cb_status = circuit_breaker.status()
    open_count = sum(1 for s in cb_status.values() if s == "open")
    scores["services"] = max(0, 100 - open_count * 25)

    total_health = round(sum(scores.values()) / len(scores), 1)

    return ok({
        "health_score":   total_health,
        "breakdown":      scores,
        "memory_pct":     mem.percent,
        "cpu_pct":        cpu,
        "cache_size":     result_cache.size(),
        "circuit_status": cb_status,
        "timestamp":      datetime.utcnow().isoformat()
    })

@router.get("/heatmap")
async def confidence_heatmap():
    """Confidence Heatmap — أي طبقة تسبب المشاكل"""
    db = get_db()
    ratings = await db.ratings.find({}).to_list(1000)
    tools = {}
    for r in ratings:
        t = r.get("tool","unknown")
        if t not in tools:
            tools[t] = {"likes": 0, "dislikes": 0}
        if r.get("rating") == "like":
            tools[t]["likes"] += 1
        else:
            tools[t]["dislikes"] += 1
    heatmap = {t: round(v["likes"]/(v["likes"]+v["dislikes"])*100, 1)
               if (v["likes"]+v["dislikes"]) > 0 else 0
               for t, v in tools.items()}
    return ok({"heatmap": heatmap})

@router.get("/timeline")
async def threat_timeline():
    """Threat Timeline — خط زمني للتهديدات"""
    db = get_db()
    pipeline = [
        {"$match": {"threat_level": {"$gte": 60}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "count": {"$sum": 1},
            "avg_threat": {"$avg": "$threat_level"}
        }},
        {"$sort": {"_id": -1}},
        {"$limit": 30}
    ]
    try:
        data = await db.scans.aggregate(pipeline).to_list(30)
        return ok({"timeline": data})
    except Exception:
        return ok({"timeline": []})

@router.get("/learning")
async def learning_tracker():
    """Learning Rate Tracker"""
    db = get_db()
    pipeline = [
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$recorded_at"}},
            "likes":    {"$sum": {"$cond": [{"$eq":["$rating","like"]},1,0]}},
            "dislikes": {"$sum": {"$cond": [{"$eq":["$rating","dislike"]},1,0]}},
            "total":    {"$sum": 1}
        }},
        {"$sort": {"_id": -1}},
        {"$limit": 30}
    ]
    try:
        data = await db.ratings.aggregate(pipeline).to_list(30)
        return ok({"learning": data})
    except Exception:
        return ok({"learning": []})

@router.get("/cells")
async def cells_status():
    db = get_db()
    cells = await db.cells.find({}, {"_id": 0}).to_list(50)
    return ok({"cells": cells, "count": len(cells)})

# WebSocket للإحصائيات المباشرة
active_ws: list = []

@router.websocket("/ws/stats")
async def ws_stats(ws: WebSocket):
    await ws.accept()
    active_ws.append(ws)
    try:
        while True:
            db = get_db()
            mem = psutil.virtual_memory()
            data = {
                "users":      await db.users.count_documents({}),
                "scans":      await db.scans.count_documents({}),
                "memory_pct": mem.percent,
                "cache_size": result_cache.size(),
                "timestamp":  datetime.utcnow().isoformat()
            }
            await ws.send_text(json.dumps(data))
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        active_ws.remove(ws)
    except Exception:
        if ws in active_ws:
            active_ws.remove(ws)
