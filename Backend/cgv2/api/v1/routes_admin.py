"""Admin Routes"""
from fastapi import APIRouter, Request
from db.schemas import TrainRequest, BanRequest, ok, err
from db.mongodb import get_db
from systems.trainer import run_training
from config import settings
from utils.logger import logger
from datetime import datetime
import psutil

router = APIRouter(prefix="/admin", tags=["Admin"])

def _check_admin(request: Request) -> bool:
    return request.state.user_id == settings.ADMIN_ID

@router.post("/train")
async def train(req: TrainRequest, request: Request):
    if not _check_admin(request):
        return err("Admin only", "AUTH_ERROR")
    if not req.confirm:
        return err("Set confirm=true to start training", "VALIDATION_ERROR")
    result = await run_training()
    logger.info("manual_training", admin=request.state.user_id)
    return ok(result)

@router.get("/stats")
async def stats(request: Request):
    if not _check_admin(request):
        return err("Admin only", "AUTH_ERROR")
    db = get_db()
    users_count     = await db.users.count_documents({"is_banned": False})
    knowledge_count = await db.knowledge.count_documents({"deleted": {"$ne": True}})
    scans_count     = await db.scans.count_documents({})
    ratings_count   = await db.ratings.count_documents({})
    hypo_count      = await db.hypotheses.count_documents({"status": "pending"})

    from systems.cache import result_cache
    from systems.circuit_breaker import circuit_breaker
    mem = psutil.virtual_memory()

    return ok({
        "users":         users_count,
        "knowledge":     knowledge_count,
        "scans":         scans_count,
        "ratings":       ratings_count,
        "hypotheses":    hypo_count,
        "cache_size":    result_cache.size(),
        "memory_used_pct": mem.percent,
        "circuit_breakers": circuit_breaker.status(),
        "timestamp":     datetime.utcnow().isoformat()
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
    logger.warning("user_banned", target=req.user_id, reason=req.reason,
                   admin=request.state.user_id)
    return ok({"banned": True, "user_id": req.user_id})

@router.get("/users")
async def list_users(request: Request):
    if not _check_admin(request):
        return err("Admin only", "AUTH_ERROR")
    db = get_db()
    users = await db.users.find({}, {
        "_id":0,"password":0,"api_key":0
    }).sort("points",-1).limit(50).to_list(50)
    return ok({"users": users, "count": len(users)})

@router.get("/logs")
async def get_logs(request: Request):
    if not _check_admin(request):
        return err("Admin only", "AUTH_ERROR")
    db = get_db()
    logs = await db.logs.find({}, {"_id":0}).sort(
        "timestamp",-1).limit(100).to_list(100)
    return ok({"logs": logs})
