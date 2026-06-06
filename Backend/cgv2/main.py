"""
CyberGuard Backend V2 — Entry Point
17-Layer Neural Engine + File Scanner + Dashboard
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime
import uvicorn, psutil

from config import settings
from utils.logger import setup_logging, logger
from db.mongodb import connect, disconnect
from api.middleware import AuthMiddleware
from api.v1.routes_auth      import router as auth_router
from api.v1.routes_analyze   import router as analyze_router
from api.v1.routes_scan      import router as scan_router
from api.v1.routes_admin     import router as admin_router
from api.v1.routes_dashboard import router as dashboard_router
from systems.scheduler       import setup_scheduler, scheduler
from systems.memory_monitor  import check_and_free

setup_logging()
settings.validate_critical()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("cyberguard_starting", version="2.0",
                env=settings.ENVIRONMENT)
    await connect()
    setup_scheduler()

    # Memory monitor كل دقيقتين
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    scheduler.add_job(check_and_free, "interval", minutes=2,
                      id="memory_monitor")

    logger.info("cyberguard_started", port=settings.PORT)
    yield

    # Shutdown
    logger.info("cyberguard_stopping")
    scheduler.shutdown(wait=True)
    await disconnect()
    logger.info("cyberguard_stopped")

app = FastAPI(
    title="CyberGuard API",
    description="17-Layer Neural Cybersecurity Engine V2",
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

# Routers — Versioned API
PREFIX = "/api/v1"
app.include_router(auth_router,      prefix=PREFIX)
app.include_router(analyze_router,   prefix=PREFIX)
app.include_router(scan_router,      prefix=PREFIX)
app.include_router(admin_router,     prefix=PREFIX)
app.include_router(dashboard_router, prefix=PREFIX)

# System Endpoints
@app.get("/")
def root():
    return {
        "service":  "CyberGuard API",
        "version":  "2.0.0",
        "status":   "running",
        "layers":   17,
        "docs":     "/docs",
        "health":   "/health",
    }

@app.get("/health")
def health():
    """UptimeRobot endpoint"""
    return {"status": "online", "timestamp": datetime.utcnow().isoformat()}

@app.get("/ping")
def ping():
    """Lightweight ping for UptimeRobot"""
    return {"pong": True, "ts": int(datetime.utcnow().timestamp())}

# Global error handler
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
