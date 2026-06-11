"""Admin Routes — مع Neural Knowledge Engine"""
from fastapi import APIRouter, Request
from db.schemas import TrainRequest, BanRequest, ok, err
from db.mongodb import get_db
from systems.trainer import run_training
from engine.pipeline import get_learning_layer
from config import settings
from utils.logger import logger
from datetime import datetime
import psutil

router = APIRouter(prefix="/admin", tags=["Admin"])

def _check_admin(request: Request) -> bool:
    return request.state.user_id == settings.ADMIN_ID

def _get_neural_engine(request: Request):
    return request.app.state.get_neural_engine()

@router.post("/train")
async def train(req: TrainRequest, request: Request):
    if not _check_admin(request):
        return err("Admin only", "AUTH_ERROR")
    if not req.confirm:
        return err("Set confirm=true to start training", "VALIDATION_ERROR")

    neural_engine = _get_neural_engine(request)

    # Full training: Neural weights + Cell evolution + Hypothesis validation
    neural_result = await neural_engine.train_weekly(get_learning_layer())
    weights_result = await run_training()

    logger.info("manual_training_complete", admin=request.state.user_id)
    return ok({
        "neural":  neural_result,
        "weights": weights_result,
        "timestamp": datetime.utcnow().isoformat(),
    })

@router.get("/stats")
async def stats(request: Request):
    if not _check_admin(request):
        return err("Admin only", "AUTH_ERROR")
    db  = get_db()
    mem = psutil.virtual_memory()
    from systems.cache import result_cache
    from systems.circuit_breaker import circuit_breaker

    return ok({
        "users":            await db.users.count_documents({"is_banned":False}),
        "knowledge":        await db.knowledge.count_documents({"deleted":{"$ne":True}}),
        "knowledge_sandbox":await db.knowledge_sandbox.count_documents({"status":"pending"}),
        "cells":            await db.cells.count_documents({"is_retired":False}),
        "cells_retired":    await db.cells.count_documents({"is_retired":True}),
        "hypotheses":       await db.hypotheses.count_documents({}),
        "hypotheses_confirmed": await db.hypotheses.count_documents({"status":"confirmed"}),
        "scans":            await db.scans.count_documents({}),
        "ratings":          await db.ratings.count_documents({}),
        "cache_size":       result_cache.size(),
        "memory_used_pct":  mem.percent,
        "circuit_breakers": circuit_breaker.status(),
        "timestamp":        datetime.utcnow().isoformat(),
    })

@router.post("/ban")
async def ban_user(req: BanRequest, request: Request):
    if not _check_admin(request):
        return err("Admin only", "AUTH_ERROR")
    db = get_db()
    await db.users.update_one(
        {"user_id": req.user_id},
        {"$set": {"is_banned": True, "ban_reason": req.reason,
                  "banned_at": datetime.utcnow()}}
    )
    logger.warning("user_banned", target=req.user_id,
                   reason=req.reason, admin=request.state.user_id)
    return ok({"banned": True, "user_id": req.user_id})

@router.get("/users")
async def list_users(request: Request):
    if not _check_admin(request):
        return err("Admin only", "AUTH_ERROR")
    db    = get_db()
    users = await db.users.find(
        {}, {"_id":0,"password":0,"api_key":0}
    ).sort("points",-1).limit(50).to_list(50)
    return ok({"users": users, "count": len(users)})

@router.get("/logs")
async def get_logs(request: Request):
    if not _check_admin(request):
        return err("Admin only", "AUTH_ERROR")
    db   = get_db()
    logs = await db.logs.find({},{"_id":0}).sort(
        "timestamp",-1).limit(100).to_list(100)
    return ok({"logs": logs})

@router.get("/cells")
async def get_cells(request: Request):
    if not _check_admin(request):
        return err("Admin only", "AUTH_ERROR")
    db    = get_db()
    cells = await db.cells.find({},{"_id":0}).to_list(200)
    return ok({"cells": cells, "total": len(cells)})

@router.post("/cells/retire")
async def retire_cells(request: Request):
    if not _check_admin(request):
        return err("Admin only", "AUTH_ERROR")
    neural_engine = _get_neural_engine(request)
    await neural_engine.cells.retire_weak_cells()
    return ok({"status": "retirement_check_done"})

@router.get("/hypotheses")
async def get_hypotheses(request: Request):
    if not _check_admin(request):
        return err("Admin only", "AUTH_ERROR")
    db    = get_db()
    hypos = await db.hypotheses.find({},{"_id":0}).to_list(100)
    return ok({"hypotheses": hypos, "count": len(hypos)})

@router.post("/sandbox/process")
async def process_sandbox(request: Request):
    """معالجة المعرفة المعلقة في الـ Sandbox"""
    if not _check_admin(request):
        return err("Admin only", "AUTH_ERROR")
    neural_engine = _get_neural_engine(request)
    pending = await neural_engine.sandbox.get_pending()
    processed = 0
    for item in pending[:20]:
        await neural_engine.sandbox.verify(item["key"])
        processed += 1
    return ok({"processed": processed, "total_pending": len(pending)})
