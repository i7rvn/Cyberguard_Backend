"""Auth Routes — Register / Login / Refresh"""
from fastapi import APIRouter, Depends
from fastapi.requests import Request
from datetime import datetime
from db.mongodb import get_db
from db.schemas import UserRegister, UserLogin, ok, err
from utils.security import hash_password, verify_password, create_token
from utils.logger import logger
import uuid

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register")
async def register(data: UserRegister, request: Request):
    db = get_db()
    existing = await db.users.find_one({"username": data.username})
    if existing:
        return err("Username already exists", "VALIDATION_ERROR")
    user = {
        "user_id":    abs(hash(data.username)) % 10**9,
        "username":   data.username,
        "password":   hash_password(data.password),
        "api_key":    str(uuid.uuid4()).replace("-",""),
        "points":     0,
        "level":      "Bronze",
        "reputation": 1.0,
        "trust_score":1.0,
        "risk_score": 0.0,
        "abuse_score":0.0,
        "badges":     [],
        "is_banned":  False,
        "is_admin":   False,
        "created_at": datetime.utcnow(),
        "last_seen":  datetime.utcnow(),
    }
    await db.users.insert_one(user)
    token = create_token({"user_id": user["user_id"], "username": data.username})
    logger.info("user_registered", username=data.username)
    return ok({"access_token": token, "token_type": "bearer",
               "user_id": user["user_id"], "username": data.username})

@router.post("/login")
async def login(data: UserLogin, request: Request):
    db = get_db()
    user = await db.users.find_one({"username": data.username})
    if not user or not verify_password(data.password, user["password"]):
        return err("Invalid credentials", "AUTH_ERROR")
    if user.get("is_banned"):
        return err("Account banned", "AUTH_ERROR")
    await db.users.update_one(
        {"username": data.username},
        {"$set": {"last_seen": datetime.utcnow()}}
    )
    token = create_token({"user_id": user["user_id"], "username": data.username})
    logger.info("user_login", username=data.username)
    return ok({"access_token": token, "token_type": "bearer",
               "user_id": user["user_id"], "username": data.username,
               "points": user["points"], "level": user["level"]})

@router.post("/refresh")
async def refresh(request: Request):
    user_id = request.state.user_id
    db = get_db()
    user = await db.users.find_one({"user_id": user_id})
    if not user:
        return err("User not found", "AUTH_ERROR")
    token = create_token({"user_id": user_id, "username": user["username"]})
    return ok({"access_token": token, "token_type": "bearer"})
