"""File Scan Routes"""
from fastapi import APIRouter, UploadFile, File, Depends, Request, Form
from db.schemas import ScanProfile, ok, err
from scanner.file_scanner import file_scanner
from db.mongodb import get_db
from api.middleware import rate_limit_check
from utils.logger import logger

router = APIRouter(prefix="/scan", tags=["Scanner"])

@router.post("/upload")
async def upload_and_scan(
    request: Request,
    file: UploadFile = File(...),
    profile: str = Form(default="normal"),
    _=Depends(rate_limit_check)
):
    user_id = request.state.user_id or 0
    try:
        prof = ScanProfile(profile)
    except ValueError:
        prof = ScanProfile.NORMAL

    if not file.filename:
        return err("No file provided", "VALIDATION_ERROR")

    result = await file_scanner.scan(file, prof, user_id)
    if "error" in result:
        return err(result["error"], "VALIDATION_ERROR")
    return ok(result)

@router.get("/{scan_id}")
async def get_scan(scan_id: str, request: Request):
    db = get_db()
    scan = await db.scans.find_one({"scan_id": scan_id}, {"_id": 0})
    if not scan:
        return err("Scan not found", "NOT_FOUND")
    scan.pop("created_at", None)
    return ok(scan)

@router.get("/user/history")
async def scan_history(request: Request):
    user_id = request.state.user_id or 0
    db = get_db()
    scans = await db.scans.find(
        {"user_id": user_id},
        {"_id": 0, "filename": 1, "scan_id": 1, "threat_score": 1,
         "verdict": 1, "real_type": 1, "status": 1}
    ).sort("created_at", -1).limit(20).to_list(20)
    return ok({"scans": scans, "count": len(scans)})
