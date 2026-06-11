"""
CyberGuard Backend V2 — Final Complete Entry Point
17-Layer Neural Engine + Knowledge Graph + Cell Evolution + File Scanner + Dashboard
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime
import uvicorn, psutil

from config import settings
from utils.logger import setup_logging, logger
from db.mongodb import connect, disconnect, get_db
from api.middleware import AuthMiddleware
from api.v1.routes_auth      import router as auth_router
from api.v1.routes_analyze   import router as analyze_router
from api.v1.routes_scan      import router as scan_router
from api.v1.routes_admin     import router as admin_router
from api.v1.routes_dashboard import router as dashboard_router
from visualization.neural_ws_route import router as neural_ws_router
from systems.scheduler       import setup_scheduler, scheduler
from systems.memory_monitor  import check_and_free
from neural_knowledge_engine import NeuralKnowledgeEngine

setup_logging()
settings.validate_critical()

# Global engine instance
neural_engine: NeuralKnowledgeEngine = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global neural_engine

    logger.info("cyberguard_starting", version="2.0", env=settings.ENVIRONMENT)

    # Connect MongoDB
    await connect()
    db = get_db()

    # Init Neural Knowledge Engine
    neural_engine = NeuralKnowledgeEngine(db)
    await neural_engine.startup()
    logger.info("neural_engine_started", cells="initialized")

    # Setup Scheduler
    setup_scheduler()

    # Memory monitor every 2 minutes
    scheduler.add_job(check_and_free, "interval", minutes=2, id="memory_monitor")

    # Weekly full training — includes cell evolution + hypothesis validation
    async def weekly_full_train():
        from systems.trainer import run_training
        from engine.pipeline import get_learning_layer
        await neural_engine.train_weekly(get_learning_layer())
        await run_training()

    scheduler.add_job(weekly_full_train, "cron",
                      day_of_week="sun", hour=4, minute=0, id="weekly_train")

    # Daily cell retirement check
    scheduler.add_job(
        lambda: neural_engine.cells.retire_weak_cells(),
        "cron", hour=3, minute=0, id="daily_retire"
    )

    logger.info("cyberguard_started", port=settings.PORT)
    yield

    logger.info("cyberguard_stopping")
    scheduler.shutdown(wait=True)
    await disconnect()
    logger.info("cyberguard_stopped")

app = FastAPI(
    title="CyberGuard API",
    description="17-Layer Neural Knowledge Engine V2 — Cell Evolution + Knowledge Graph",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth Middleware
auth_mw = AuthMiddleware()
app.middleware("http")(auth_mw)

# Dependency injection for neural_engine
def get_neural_engine() -> NeuralKnowledgeEngine:
    return neural_engine

app.state.get_neural_engine = get_neural_engine

# Routers
PREFIX = "/api/v1"
app.include_router(auth_router,       prefix=PREFIX)
app.include_router(analyze_router,    prefix=PREFIX)
app.include_router(scan_router,       prefix=PREFIX)
app.include_router(admin_router,      prefix=PREFIX)
app.include_router(dashboard_router,  prefix=PREFIX)
app.include_router(neural_ws_router,  prefix=PREFIX + "/dashboard")

@app.get("/")
def root():
    return {
        "service":  "CyberGuard API",
        "version":  "2.0.0",
        "status":   "running",
        "layers":   17,
        "features": [
            "Neural Knowledge Engine",
            "Cell Evolution System",
            "Knowledge Graph",
            "Discovery Engine",
            "Reward/Punishment System",
            "File Scanner",
            "WebSocket Dashboard",
        ],
        "docs":   "/docs",
        "health": "/health",
    }

@app.get("/health")
def health():
    return {"status": "online", "timestamp": datetime.utcnow().isoformat()}

@app.get("/ping")
def ping():
    return {"pong": True, "ts": int(datetime.utcnow().timestamp())}

@app.exception_handler(Exception)
async def global_error(request, exc):
    logger.error("unhandled_error", error=str(exc), path=request.url.path)
    return JSONResponse(
        {"success": False, "error": f"SYSTEM_ERROR: {str(exc)}"}, 500)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
        workers=1,
    )
