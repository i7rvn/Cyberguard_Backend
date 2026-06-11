"""Layer 7: Reputation — User Trust/Risk/Abuse Scores"""
from layers.base import BaseLayer
from engine.context import AnalysisContext
from db.mongodb import get_db
from datetime import datetime

class ReputationLayer(BaseLayer):
    name = "layer07_reputation"
    critical = False
    weight = 0.9

    async def process(self, ctx: AnalysisContext) -> AnalysisContext:
        db = get_db()
        user = await db.users.find_one({"user_id": ctx.user_id}) or {}
        reputation   = user.get("reputation", 1.0)
        trust_score  = user.get("trust_score", 1.0)
        risk_score   = user.get("risk_score", 0.0)
        abuse_score  = user.get("abuse_score", 0.0)

        level = ("expert" if reputation >= 50 else
                 "trusted" if reputation >= 10 else "normal")

        ctx.add_result("reputation", {
            "user_reputation": reputation,
            "trust_score":     trust_score,
            "risk_score":      risk_score,
            "abuse_score":     abuse_score,
            "level":           level
        })
        return ctx

    @staticmethod
    async def update(user_id: int, correct: bool):
        db = get_db()
        user = await db.users.find_one({"user_id": user_id}) or {}
        rep = user.get("reputation", 1.0)
        rep = min(100.0, rep * 1.1) if correct else max(0.1, rep * 0.9)
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"reputation": round(rep, 4),
                      "last_seen": datetime.utcnow()}}
        )
