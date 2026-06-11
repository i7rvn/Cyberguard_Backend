"""Dashboard Routes + WebSocket — مع Neural Knowledge Engine"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from db.schemas import ok, err
from db.mongodb import get_db
from systems.circuit_breaker import circuit_breaker
from systems.cache import result_cache
from visualization.ws_events import register_client, unregister_client
from datetime import datetime
import asyncio, json, psutil

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

def _get_neural_engine(request: Request):
    return request.app.state.get_neural_engine()

@router.get("/health")
async def health_score(request: Request):
    db  = get_db()
    mem = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.1)

    scores = {
        "memory":   max(0, 100 - mem.percent),
        "cpu":      max(0, 100 - cpu),
        "services": max(0, 100 - sum(
            1 for s in circuit_breaker.status().values() if s == "open") * 25),
    }

    # Cell health
    cells = await db.cells.find({"is_retired": False}).to_list(50)
    if cells:
        avg_rep = sum(c.get("reputation",50) for c in cells) / len(cells)
        scores["cells"] = min(100, avg_rep)

    total_health = round(sum(scores.values()) / len(scores), 1)

    return ok({
        "health_score":   total_health,
        "breakdown":      scores,
        "memory_pct":     mem.percent,
        "cpu_pct":        cpu,
        "cache_size":     result_cache.size(),
        "circuit_status": circuit_breaker.status(),
        "timestamp":      datetime.utcnow().isoformat(),
    })

@router.get("/cells")
async def cells_status(request: Request):
    db    = get_db()
    cells = await db.cells.find(
        {"is_retired": False}, {"_id": 0}
    ).to_list(100)
    return ok({"cells": cells, "count": len(cells)})

@router.get("/cells/graph")
async def cells_graph(request: Request):
    """بيانات الرسم البياني للخلايا والروابط"""
    neural_engine = _get_neural_engine(request)
    graph_data    = await neural_engine.graph.get_graph_data()
    return ok(graph_data)

@router.get("/hypotheses")
async def get_hypotheses():
    db = get_db()
    hypos = await db.hypotheses.find(
        {}, {"_id": 0}
    ).sort("discovered_at", -1).limit(50).to_list(50)
    return ok({"hypotheses": hypos, "count": len(hypos)})

@router.get("/heatmap")
async def confidence_heatmap():
    db      = get_db()
    ratings = await db.ratings.find({}).to_list(1000)
    tools   = {}
    for r in ratings:
        t = r.get("tool","unknown")
        if t not in tools:
            tools[t] = {"likes": 0, "dislikes": 0}
        if r.get("rating") == "like":
            tools[t]["likes"] += 1
        else:
            tools[t]["dislikes"] += 1
    heatmap = {
        t: round(v["likes"]/(v["likes"]+v["dislikes"])*100,1)
        if (v["likes"]+v["dislikes"]) > 0 else 0
        for t,v in tools.items()
    }
    return ok({"heatmap": heatmap})

@router.get("/timeline")
async def threat_timeline():
    db = get_db()
    pipeline = [
        {"$match": {"threat_level": {"$gte": 60}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "count": {"$sum": 1},
            "avg_threat": {"$avg": "$threat_level"}
        }},
        {"$sort": {"_id": -1}}, {"$limit": 30}
    ]
    try:
        data = await db.scans.aggregate(pipeline).to_list(30)
        return ok({"timeline": data})
    except Exception:
        return ok({"timeline": []})

@router.get("/learning")
async def learning_tracker():
    db = get_db()
    pipeline = [
        {"$group": {
            "_id": {"$dateToString": {"format":"%Y-%m-%d","date":"$recorded_at"}},
            "likes":    {"$sum": {"$cond":[{"$eq":["$rating","like"]},1,0]}},
            "dislikes": {"$sum": {"$cond":[{"$eq":["$rating","dislike"]},1,0]}},
            "total":    {"$sum": 1}
        }},
        {"$sort": {"_id": -1}}, {"$limit": 30}
    ]
    try:
        data = await db.ratings.aggregate(pipeline).to_list(30)
        return ok({"learning": data})
    except Exception:
        return ok({"learning": []})

@router.get("/knowledge/sandbox")
async def sandbox_status():
    db = get_db()
    pending  = await db.knowledge_sandbox.count_documents({"status":"pending"})
    approved = await db.knowledge_sandbox.count_documents({"status":"approved"})
    rejected = await db.knowledge_sandbox.count_documents({"status":"rejected"})
    return ok({"pending": pending, "approved": approved, "rejected": rejected})

@router.get("/stats")
async def full_stats():
    db = get_db()
    return ok({
        "users":         await db.users.count_documents({}),
        "knowledge":     await db.knowledge.count_documents({"verified":True}),
        "sandbox":       await db.knowledge_sandbox.count_documents({"status":"pending"}),
        "cells":         await db.cells.count_documents({"is_retired":False}),
        "hypotheses":    await db.hypotheses.count_documents({}),
        "scans":         await db.scans.count_documents({}),
        "discoveries":   await db.hypotheses.count_documents({"status":"confirmed"}),
        "cache_size":    result_cache.size(),
        "timestamp":     datetime.utcnow().isoformat(),
    })

# WebSocket — Stats
@router.websocket("/ws/stats")
async def ws_stats(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            db  = get_db()
            mem = psutil.virtual_memory()
            data = {
                "event":      "STATS_UPDATE",
                "users":      await db.users.count_documents({}),
                "scans":      await db.scans.count_documents({}),
                "cells":      await db.cells.count_documents({"is_retired":False}),
                "knowledge":  await db.knowledge.count_documents({"verified":True}),
                "memory_pct": mem.percent,
                "cache_size": result_cache.size(),
                "timestamp":  datetime.utcnow().isoformat(),
            }
            await ws.send_text(json.dumps(data))
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
