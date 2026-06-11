"""Layer 8: Time — Knowledge Aging Engine"""
from layers.base import BaseLayer
from engine.context import AnalysisContext
from datetime import datetime, timedelta
import json, os

TIME_FILE = "data/knowledge/time_tracker.json"

AGING_DAYS = {
    "cve": 30, "malware": 14, "phishing": 7,
    "malicious_links": 30, "password_strength": 365,
    "sql_injection": 365, "xss": 365,
}

class TimeLayer(BaseLayer):
    name = "layer08_time"
    critical = False
    weight = 0.7

    def __init__(self):
        self.data = self._load()

    def _load(self):
        if os.path.exists(TIME_FILE):
            try:
                with open(TIME_FILE) as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save(self):
        os.makedirs("data/knowledge", exist_ok=True)
        with open(TIME_FILE, "w") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    async def process(self, ctx: AnalysisContext) -> AnalysisContext:
        key = ctx.key
        expiry_days = AGING_DAYS.get(ctx.tool, 180)
        now = datetime.utcnow()

        if key not in self.data:
            self.data[key] = {
                "created": now.isoformat(),
                "last_verified": now.isoformat(),
                "expiry": (now + timedelta(days=expiry_days)).isoformat(),
                "tool": ctx.tool
            }
            self._save()
            ctx.add_result("time", {"age_days": 0, "expired": False, "new": True})
        else:
            info   = self.data[key]
            created = datetime.fromisoformat(info["created"])
            expiry  = datetime.fromisoformat(info["expiry"])
            age_days = (now - created).days
            expired  = now > expiry
            ctx.add_result("time", {
                "age_days": age_days,
                "expired":  expired,
                "expiry":   info["expiry"]
            })
            if expired:
                self.data[key]["expiry"] = (now + timedelta(days=expiry_days)).isoformat()
                self.data[key]["last_verified"] = now.isoformat()
                self._save()
        return ctx
