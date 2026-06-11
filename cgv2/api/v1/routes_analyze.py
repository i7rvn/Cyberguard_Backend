"""Analysis Routes — مع Neural Knowledge Engine"""
from fastapi import APIRouter, Depends, Request
from db.schemas import AnalyzeRequest, RateRequest, ok, err
from engine.pipeline import run_pipeline, get_trust_layer, get_learning_layer
from systems.cache import result_cache
from layers.layer06_human import HumanFeedbackLayer
from layers.layer07_reputation import ReputationLayer
from layers.layer10_experience import ExperienceLayer
from db.mongodb import get_db
from api.middleware import rate_limit_check, fingerprint_request
from utils.logger import logger
from utils.feature_extractor import FeatureExtractor
from datetime import datetime
import time

router = APIRouter(prefix="/analyze", tags=["Analysis"])
features = FeatureExtractor()

def _get_neural_engine(request: Request):
    return request.app.state.get_neural_engine()

@router.post("")
async def analyze(req: AnalyzeRequest, request: Request,
                  _=Depends(rate_limit_check)):
    t0      = time.time()
    user_id = request.state.user_id or 0

    # Cache check
    cache_key = f"{req.tool}:{req.input_data[:80]}"
    cached = result_cache.get(cache_key)
    if cached:
        cached["from_cache"] = True
        return ok(cached, time_ms=round((time.time()-t0)*1000,2),
                  req_id=request.state.request_id)

    # Run 17-layer pipeline
    ctx = await run_pipeline(req.tool, req.input_data, user_id, req.profile.value)

    # Run Neural Knowledge Engine in parallel
    neural_engine = _get_neural_engine(request)
    search_items  = ctx.results.get("collector", {}).get("items", [])
    neural_result = await neural_engine.process(
        tool=req.tool,
        input_data=req.input_data,
        search_results=search_items,
        user_id=user_id,
    )

    result = {
        "key":              ctx.key,
        "tool":             ctx.tool,
        "threat_level":     ctx.threat_level,
        "accuracy":         ctx.accuracy,
        "confidence":       neural_result["confidence"],   # من Confidence Engine الجديد
        "explanation":      ctx.explanation,
        "inferences":       ctx.inferences,
        "neural_knowledge": {
            "cell_type":       neural_result["cell_type"],
            "knowledge_added": neural_result["knowledge_added"],
            "discoveries":     neural_result["discoveries"],
            "concepts":        neural_result["concepts"],
        },
        "processing_time_ms": round(ctx.elapsed_ms(), 2),
        "timestamp":        datetime.utcnow().isoformat(),
        "bypassed_layers":  ctx.bypassed_layers,
        "safe_mode":        ctx.safe_mode,
    }

    # Save to DB
    db = get_db()
    await db.scans.update_one(
        {"key": ctx.key, "user_id": user_id},
        {"$set": {**result, "input_preview": req.input_data[:100]}},
        upsert=True
    )

    # Cache result 1 hour
    result_cache.set(cache_key, result, ttl=3600)

    logger.info("analysis_complete", tool=req.tool,
                threat=ctx.threat_level, user=user_id,
                discoveries=neural_result["discoveries"])
    return ok(result, time_ms=round((time.time()-t0)*1000,2),
              req_id=request.state.request_id)

@router.post("/url")
async def analyze_url(request: Request, _=Depends(rate_limit_check)):
    body = await request.json()
    url  = body.get("url","")
    if not url:
        return err("URL required", "VALIDATION_ERROR")
    req = AnalyzeRequest(tool="malicious_links", input_data=url)
    return await analyze(req, request)

@router.post("/hash")
async def analyze_hash(request: Request, _=Depends(rate_limit_check)):
    body = await request.json()
    h    = body.get("hash","")
    if not h:
        return err("Hash required", "VALIDATION_ERROR")
    req = AnalyzeRequest(tool="hash_check", input_data=h)
    return await analyze(req, request)

@router.post("/rate")
async def rate_result(req: RateRequest, request: Request):
    user_id = request.state.user_id or 0
    db      = get_db()

    user       = await db.users.find_one({"user_id": user_id}) or {}
    reputation = user.get("reputation", 1.0)

    # Old system — update trust + weights
    feedback = await HumanFeedbackLayer.record_rating(
        req.key, user_id, req.rating.value, reputation)
    trust_layer = get_trust_layer()
    trust_layer.update_human(req.key, req.rating.value, reputation)

    learning = get_learning_layer()
    scan = await db.scans.find_one({"key": req.key})
    if scan:
        fv = features.extract(scan.get("tool",""), scan.get("input_preview",""))
        learning.update(scan.get("tool",""), fv,
                        1.0 if req.rating.value == "like" else 0.0)
        await ExperienceLayer.record(
            scan.get("tool",""), req.key,
            scan.get("threat_level",0), req.rating.value, user_id)

    # New system — Neural Knowledge Engine feedback
    neural_engine = _get_neural_engine(request)
    neural_feedback = await neural_engine.feedback(
        key=req.key,
        tool=scan.get("tool","") if scan else req.key,
        rating=req.rating.value,
        prediction=(scan.get("threat_level",50)/100) if scan else 0.5,
    )

    await ReputationLayer.update(user_id, req.rating.value == "like")
    points = 10 if req.rating.value == "like" else 2
    await db.users.update_one(
        {"user_id": user_id}, {"$inc": {"points": points}}
    )
    result_cache.invalidate(req.key)

    return ok({
        "recorded":     True,
        "effect":       feedback["effect"],
        "points_earned":points,
        "neural_rewards":neural_feedback.get("rewards",[]),
        "cell_updated": neural_feedback.get("net_score",0),
    })

@router.get("/result/{key}")
async def get_result(key: str, request: Request):
    db   = get_db()
    scan = await db.scans.find_one({"key": key}, {"_id": 0})
    if not scan:
        return err("Result not found", "NOT_FOUND")
    return ok(scan)
