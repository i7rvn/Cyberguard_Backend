"""Layer 12: Smart Forgetting"""
from layers.base import BaseLayer
from engine.context import AnalysisContext
from db.mongodb import get_db
from datetime import datetime
import json, os

TRUST_FILE = "data/knowledge/trust_scores.json"

class ForgettingLayer(BaseLayer):
    name = "layer12_forgetting"
    critical = False
    weight = 0.5

    async def process(self, ctx: AnalysisContext) -> AnalysisContext:
        ctx.add_result("forgetting", {"status": "monitored"})
        return ctx

    @staticmethod
    async def run_cleanup():
        """يُشغَّل من Scheduler"""
        if not os.path.exists(TRUST_FILE):
            return {"forgotten": 0}
        with open(TRUST_FILE) as f:
            scores = json.load(f)
        from config import settings
        to_delete = [k for k, v in scores.items()
                     if v.get("trust", 1.0) < settings.FORGET_THRESHOLD]
        for k in to_delete:
            del scores[k]
        with open(TRUST_FILE, "w") as f:
            json.dump(scores, f, indent=2)

        db = get_db()
        result = await db.knowledge.update_many(
            {"trust": {"$lt": settings.FORGET_THRESHOLD}},
            {"$set": {"deleted": True, "deleted_at": datetime.utcnow()}}
        )
        return {"forgotten": len(to_delete) + result.modified_count}
