"""
Knowledge Sandbox — كل معرفة جديدة تدخل هنا أولاً
"""
from datetime import datetime
from knowledge.confidence_engine import ConfidenceEngine

confidence_engine = ConfidenceEngine()

class KnowledgeSandbox:
    def __init__(self, db):
        self.db = db

    async def submit(self, key: str, raw_data: dict,
                     cell_type: str, sources: list) -> dict:
        """أدخل معرفة للـ Sandbox"""
        entry = {
            "key":       key,
            "cell_type": cell_type,
            "raw_data":  raw_data,
            "sources":   sources,
            "status":    "pending",
            "submitted_at": datetime.utcnow().isoformat(),
        }
        await self.db.knowledge_sandbox.update_one(
            {"key": key}, {"$setOnInsert": entry}, upsert=True
        )
        return entry

    async def verify(self, key: str, cell_reputation: float = 50.0,
                     human_ratings: int = 0,
                     scan_result: dict = None) -> dict:
        """تحقق من المعرفة وقرر هل تدخل قاعدة المعرفة"""
        doc = await self.db.knowledge_sandbox.find_one({"key": key})
        if not doc:
            return {"approved": False, "reason": "not_found"}

        sources = doc.get("sources", [])
        cb = confidence_engine.calculate(
            sources=sources,
            search_results=sources,
            cell_reputation=cell_reputation,
            human_ratings=human_ratings,
            verification_ok=len(sources) >= 2,
            scan_result=scan_result,
        )

        approved = cb.final >= 0.45

        await self.db.knowledge_sandbox.update_one(
            {"key": key},
            {"$set": {
                "status":     "approved" if approved else "rejected",
                "confidence": cb.to_dict(),
                "verified_at":datetime.utcnow().isoformat(),
            }}
        )

        if approved:
            await self.db.knowledge.update_one(
                {"key": key},
                {"$set": {
                    "sandbox":    False,
                    "verified":   True,
                    "confidence": cb.final,
                    "confidence_breakdown": cb.to_dict(),
                    "promoted_at":datetime.utcnow().isoformat(),
                }},
                upsert=True
            )

        return {
            "approved":   approved,
            "confidence": cb.to_dict(),
            "reason":     "confidence_ok" if approved else "low_confidence",
        }

    async def get_pending(self) -> list:
        return await self.db.knowledge_sandbox.find(
            {"status": "pending"}
        ).limit(50).to_list(50)
