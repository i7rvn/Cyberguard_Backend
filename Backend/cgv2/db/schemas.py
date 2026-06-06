"""Pydantic Schemas for validation"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class ScanProfile(str, Enum):
    QUICK  = "quick"
    NORMAL = "normal"
    DEEP   = "deep"

class RatingValue(str, Enum):
    LIKE    = "like"
    DISLIKE = "dislike"

# Auth
class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=100)

class UserLogin(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

# Analysis
class AnalyzeRequest(BaseModel):
    tool: str = Field(min_length=2, max_length=50)
    input_data: str = Field(min_length=1, max_length=10000)
    profile: ScanProfile = ScanProfile.NORMAL

class RateRequest(BaseModel):
    key: str
    rating: RatingValue

# Scan
class ScanRequest(BaseModel):
    profile: ScanProfile = ScanProfile.NORMAL

# Admin
class TrainRequest(BaseModel):
    confirm: bool = False

class BanRequest(BaseModel):
    user_id: int
    reason: str = ""

# Response Envelope
class Meta(BaseModel):
    version: str = "2.0"
    time_ms: float = 0
    request_id: str = ""

class Envelope(BaseModel):
    success: bool
    data: Optional[Any] = None
    meta: Meta = Meta()
    error: Optional[str] = None

def ok(data: Any, time_ms: float = 0, req_id: str = "") -> dict:
    return Envelope(success=True, data=data,
                    meta=Meta(time_ms=time_ms, request_id=req_id)).model_dump()

def err(message: str, code: str = "ERROR") -> dict:
    return Envelope(success=False, error=f"{code}: {message}").model_dump()
