"""Error Categorization"""
from fastapi import HTTPException

class AppError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        self.code = code
        self.message = message
        self.status = status

VALIDATION_ERROR  = lambda msg: AppError("VALIDATION_ERROR", msg, 422)
NETWORK_ERROR     = lambda msg: AppError("NETWORK_ERROR", msg, 503)
ANALYSIS_ERROR    = lambda msg: AppError("ANALYSIS_ERROR", msg, 500)
SYSTEM_ERROR      = lambda msg: AppError("SYSTEM_ERROR", msg, 500)
AUTH_ERROR        = lambda msg: AppError("AUTH_ERROR", msg, 401)
NOT_FOUND         = lambda msg: AppError("NOT_FOUND", msg, 404)
