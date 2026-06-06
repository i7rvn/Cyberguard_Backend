"""Layer 6: Human Feedback — Like/Dislike + Learning Rewards"""
from layers.base import BaseLayer
from engine.context import AnalysisContext
from db.mongodb import get_db
from datetime import datetime

class HumanFeedbackLayer(BaseLayer):
    name = "layer06_human"
    critical = False
    weight = 1.0

    async def process(self, ctx: AnalysisContext) -> AnalysisContext:
        db = get_db()
        key = ctx.key
        ratings = await db.ratings.find({"key": key}).to_list(100)

        if ratings:
            total_weighted = sum(r.get("weighted", 0) for r in ratings)
            count = len(ratings)
            human_score = min(20.0, max(-20.0, total_weighted * 2))
            ctx.confidence["human_score"] = round(human_score, 2)
            ctx.add_vote("human", 0.5 + total_weighted * 0.1, weight=1.0)
        else:
            ctx.confidence["human_score"] = 0.0

        ctx.add_result("human_feedback", {
            "ratings_count": len(ratings),
            "net_score": sum(r.get("weighted", 0) for r in ratings)
        })
        return ctx

    @staticmethod
    async def record_rating(key: str, user_id: int, rating: str,
                             reputation: float = 1.0):
        db = get_db()
        value = 1 if rating == "like" else -1
        weighted = value * reputation
        await db.ratings.insert_one({
            "key": key, "user_id": user_id,
            "rating": rating, "value": value,
            "weighted": weighted, "reputation": reputation,
            "timestamp": datetime.utcnow()
        })
        # Learning Reward
        return {"effect": "trust_increase" if value > 0 else "trust_decrease",
                "weighted": weighted}
