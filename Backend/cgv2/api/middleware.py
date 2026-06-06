"""JWT Auth + Rate Limiter + Request Fingerprinting"""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from collections import defaultdict
from datetime import datetime
from utils.security import decode_token
from utils.logger import logger
from config import settings
import time, uuid

# Rate limiting store
_rate_store: dict = defaultdict(list)
_fingerprints: dict = defaultdict(list)

class AuthMiddleware:
    PUBLIC_PATHS = {"/", "/health", "/ping", "/docs", "/redoc",
                    "/openapi.json", "/api/v1/auth/register", "/api/v1/auth/login"}

    async def __call__(self, request: Request, call_next):
        request.state.request_id = str(uuid.uuid4())[:8]
        request.state.user_id    = None
        request.state.start_time = time.time()

        path = request.url.path

        # Skip auth for public paths
        if path not in self.PUBLIC_PATHS:
            token = request.headers.get("Authorization", "").replace("Bearer ", "")
            if not token:
                return JSONResponse(
                    {"success": False, "error": "AUTH_ERROR: Token required"}, 401)
            payload = decode_token(token)
            if not payload:
                return JSONResponse(
                    {"success": False, "error": "AUTH_ERROR: Invalid token"}, 401)
            request.state.user_id = payload.get("user_id")

        response = await call_next(request)

        # Add request ID header
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["ngrok-skip-browser-warning"] = "true"
        return response

async def rate_limit_check(request: Request):
    """Rate limiting dependency"""
    ip = request.client.host
    now = datetime.now()
    window = [t for t in _rate_store[ip]
              if (now - t).total_seconds() < 60]
    _rate_store[ip] = window

    if len(window) >= settings.RATE_LIMIT_PER_MINUTE:
        logger.warning("rate_limit_exceeded", ip=ip, count=len(window))
        raise HTTPException(429, "Too many requests — wait a minute")

    _rate_store[ip].append(now)

def fingerprint_request(request: Request) -> dict:
    """Request fingerprinting — helper for suspicious behavior detection"""
    ip = request.client.host
    ua = request.headers.get("User-Agent", "")
    fp = f"{ip}:{ua[:50]}"
    now = datetime.now()
    _fingerprints[fp].append(now)
    recent = [t for t in _fingerprints[fp]
              if (now - t).total_seconds() < 300]
    _fingerprints[fp] = recent
    return {
        "ip": ip,
        "fingerprint": fp[:20],
        "requests_5min": len(recent),
        "suspicious": len(recent) > 100
    }
