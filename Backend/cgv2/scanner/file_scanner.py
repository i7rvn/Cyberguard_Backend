"""File Scanner — Orchestrator"""
import os, uuid, hashlib, math, re
from datetime import datetime
from fastapi import UploadFile
from db.schemas import ScanProfile
from db.mongodb import get_db
from utils.logger import logger
from config import settings

UPLOAD_DIR = "data/uploads"
MAX_SIZE   = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

MAGIC_BYTES = {
    b"PK\x03\x04":    "zip",
    b"MZ":            "exe/dll",
    b"\x7fELF":       "elf",
    b"%PDF":           "pdf",
    b"\xd0\xcf\x11\xe0": "ole/doc",
    b"PK":            "apk/zip",
    b"Rar!":          "rar",
    b"\x1f\x8b":      "gzip",
    b"\x89PNG":       "png",
    b"\xff\xd8\xff":  "jpeg",
}

DANGEROUS_PERMS = [
    "READ_SMS","SEND_SMS","READ_CONTACTS","ACCESS_FINE_LOCATION",
    "CAMERA","RECORD_AUDIO","READ_CALL_LOG","PROCESS_OUTGOING_CALLS",
    "RECEIVE_BOOT_COMPLETED","ADMIN","INSTALL_PACKAGES","DELETE_PACKAGES",
]

class FileScanner:
    async def scan(self, file: UploadFile, profile: ScanProfile,
                   user_id: int) -> dict:
        content = await file.read()
        size    = len(content)

        if size > MAX_SIZE:
            return {"error": f"File too large (max {settings.MAX_UPLOAD_SIZE_MB}MB)"}

        scan_id  = str(uuid.uuid4())
        ext      = os.path.splitext(file.filename or "")[1].lower()
        new_name = f"{uuid.uuid4().hex}.bin"
        save_path = os.path.join(UPLOAD_DIR, new_name)
        os.makedirs(UPLOAD_DIR, exist_ok=True)

        with open(save_path, "wb") as f:
            f.write(content)

        result = {
            "scan_id":   scan_id,
            "user_id":   user_id,
            "filename":  file.filename,
            "size":      size,
            "profile":   profile.value,
            "created_at":datetime.utcnow(),
            "status":    "scanning",
        }

        # QUICK: Magic Bytes + Hash
        result["hashes"]    = self._hash(content)
        result["real_type"] = self._magic_bytes(content)
        result["extension"] = ext

        if profile in (ScanProfile.NORMAL, ScanProfile.DEEP):
            result["strings"]    = self._extract_strings(content)
            result["iocs"]       = self._ioc_extract(content)
            result["yara_hits"]  = self._yara_scan(content, result["real_type"])

        if profile == ScanProfile.DEEP:
            result["entropy"]    = self._entropy(content)
            result["suspicious"] = self._deep_analysis(content, result)

        result["threat_score"] = self._score(result)
        result["verdict"]      = self._verdict(result["threat_score"])
        result["status"]       = "complete"

        db = get_db()
        await db.scans.insert_one({**result})

        logger.info("file_scanned", scan_id=scan_id, size=size,
                    threat=result["threat_score"], type=result["real_type"])
        return {k: v for k, v in result.items() if k not in ["_id","created_at"]}

    def _hash(self, data: bytes) -> dict:
        return {
            "md5":    hashlib.md5(data).hexdigest(),
            "sha1":   hashlib.sha1(data).hexdigest(),
            "sha256": hashlib.sha256(data).hexdigest(),
        }

    def _magic_bytes(self, data: bytes) -> str:
        for magic, ftype in MAGIC_BYTES.items():
            if data[:len(magic)] == magic:
                return ftype
        return "unknown"

    def _extract_strings(self, data: bytes, min_len: int = 6) -> list:
        try:
            text = data.decode("utf-8", errors="ignore")
        except Exception:
            text = data.decode("latin-1", errors="ignore")
        pattern = r'[\x20-\x7e]{' + str(min_len) + r',}'
        strings = re.findall(pattern, text)
        suspicious = [s for s in strings if any(
            k in s.lower() for k in ["http","cmd","exec","powershell",
                                     "base64","eval","shellcode","malware"]
        )]
        return {"total": len(strings), "suspicious": suspicious[:20]}

    def _ioc_extract(self, data: bytes) -> dict:
        try:
            text = data.decode("utf-8", errors="ignore")
        except Exception:
            text = data.decode("latin-1", errors="ignore")
        return {
            "urls":    re.findall(r'https?://[^\s\'"<>]{5,100}', text)[:15],
            "ips":     re.findall(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', text)[:10],
            "domains": re.findall(r'\b[a-zA-Z0-9\-]+\.[a-zA-Z]{2,6}\b', text)[:10],
            "emails":  re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', text)[:10],
            "hashes":  re.findall(r'\b[a-fA-F0-9]{32,64}\b', text)[:5],
        }

    def _yara_scan(self, data: bytes, file_type: str) -> list:
        hits = []
        patterns = {
            "Suspicious_Exec":   [b"CreateProcess", b"WinExec", b"ShellExecute"],
            "Network_Activity":  [b"WSAStartup", b"socket", b"connect"],
            "Crypto_Ransomware": [b"CryptEncrypt", b"BCryptEncrypt", b"AES"],
            "Persistence":       [b"HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run"],
            "AntiDebug":         [b"IsDebuggerPresent", b"CheckRemoteDebuggerPresent"],
        }
        for rule, sigs in patterns.items():
            if any(s in data for s in sigs):
                hits.append({"rule": rule, "severity": "high"})
        return hits

    def _entropy(self, data: bytes) -> float:
        if not data:
            return 0.0
        freq = {}
        for b in data:
            freq[b] = freq.get(b, 0) + 1
        total = len(data)
        ent   = -sum((c/total) * math.log2(c/total) for c in freq.values())
        return round(ent, 4)

    def _deep_analysis(self, data: bytes, result: dict) -> list:
        suspicious = []
        ent = result.get("entropy", 0)
        if ent > 7.0:
            suspicious.append("Very high entropy — possibly packed or encrypted")
        if ent > 7.5:
            suspicious.append("Likely obfuscated payload")
        if result.get("real_type") == "exe/dll":
            for perm in DANGEROUS_PERMS:
                if perm.encode() in data:
                    suspicious.append(f"Dangerous permission: {perm}")
        return suspicious

    def _score(self, result: dict) -> int:
        score = 0
        score += len(result.get("yara_hits", [])) * 20
        score += len(result.get("suspicious", [])) * 10
        strings = result.get("strings", {})
        score += len(strings.get("suspicious", [])) * 5
        iocs = result.get("iocs", {})
        score += min(len(iocs.get("urls",[])) * 3, 15)
        ent = result.get("entropy", 0)
        if ent > 7.0: score += 20
        elif ent > 6.5: score += 10
        return min(100, score)

    def _verdict(self, score: int) -> str:
        if score >= 80: return "🚨 Very Dangerous"
        if score >= 60: return "⚠️ Dangerous"
        if score >= 40: return "⚠️ Suspicious"
        if score >= 20: return "⚠️ Minor Warning"
        return "✅ Clean"

file_scanner = FileScanner()
