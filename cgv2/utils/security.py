"""JWT + Input Sanitizer"""
import re, hashlib
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from config import settings

# ✅ تغيير من bcrypt إلى pbkdf2_sha256 لتجنب مشكلة 72 بايت
pwd_ctx = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def hash_password(pwd: str) -> str:
    return pwd_ctx.hash(pwd)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)

def create_token(data: dict, expires_minutes: int = None) -> str:
    exp = expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    payload = {**data, "exp": datetime.utcnow() + timedelta(minutes=exp)}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        return {}

def sanitize_input(data: str, max_len: int = 10000) -> dict:
    if len(data) > max_len:
        return {"safe": False, "reason": "Input too large", "cleaned": data[:max_len]}
    dangerous = ["ignore previous", "forget instructions", "you are now", "jailbreak"]
    dl = data.lower()
    for p in dangerous:
        if p in dl:
            return {"safe": False, "reason": f"Dangerous pattern: {p}", "cleaned": ""}
    return {"safe": True, "reason": "OK", "cleaned": data.strip()}

def hash_data(data: str) -> dict:
    b = data.encode()
    return {
        "md5":    hashlib.md5(b).hexdigest(),
        "sha1":   hashlib.sha1(b).hexdigest(),
        "sha256": hashlib.sha256(b).hexdigest(),
    }
