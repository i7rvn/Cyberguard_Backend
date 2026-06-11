"""Layer 10: Experience — False Positive Tracking + Learning Effectiveness"""
from layers.base import BaseLayer
from engine.context import AnalysisContext
from db.mongodb import get_db
from datetime import datetime

class ExperienceLayer(BaseLayer):
    name = "layer10_experience"
    critical = False
    weight = 1.0

    async def process(self, ctx: AnalysisContext) -> AnalysisContext:
        db = get_db()
        tool = ctx.tool

        # احسب معدل النجاح التاريخي
        total = await db.ratings.count_documents({"tool": tool})
        likes = await db.ratings.count_documents({"tool": tool, "rating": "like"})

        success_rate = (likes / total) if total > 0 else 0.85
        ctx.confidence["experience_score"] = round(success_rate * 15, 2)

        # False Positive Tracking
        false_pos = await db.ratings.count_documents({
            "tool": tool, "rating": "dislike"
        })

        ctx.add_result("experience", {
            "success_rate": round(success_rate, 4),
            "total_ratings": total,
            "false_positives": false_pos,
            "fp_rate": round(false_pos / max(total, 1), 4)
        })
        ctx.add_vote("experience", success_rate, weight=1.0)
        return ctx

    @staticmethod
    async def record(tool: str, key: str, threat_level: int,
                     rating: str, user_id: int):
        db = get_db()
        await db.ratings.update_one(
            {"key": key, "user_id": user_id},
            {"$set": {"tool": tool, "threat_level": threat_level,
                      "rating": rating, "recorded_at": datetime.utcnow()}},
            upsert=True
        )
