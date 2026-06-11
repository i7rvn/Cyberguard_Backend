"""Layer 5: Contradiction — History + Duplicate Detection"""
import json, os
from datetime import datetime
from layers.base import BaseLayer
from engine.context import AnalysisContext

CONTRA_FILE = "data/knowledge/contradiction_history.json"

class ContradictionLayer(BaseLayer):
    name = "layer05_contradiction"
    critical = False
    weight = 0.8

    def __init__(self):
        self.history = self._load()

    def _load(self):
        if os.path.exists(CONTRA_FILE):
            try:
                with open(CONTRA_FILE) as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save(self):
        os.makedirs("data/knowledge", exist_ok=True)
        with open(CONTRA_FILE, "w") as f:
            json.dump(self.history[-500:], f, indent=2, ensure_ascii=False)

    async def process(self, ctx: AnalysisContext) -> AnalysisContext:
        key = ctx.key
        current_trust = ctx.results.get("trust", {}).get("trust", 0.5)
        contradictions = ctx.results.get("logic", {}).get("contradictions", [])

        # Duplicate Detection
        duplicate = any(h.get("key") == key for h in self.history[-200:])

        if contradictions:
            entry = {
                "key": key, "tool": ctx.tool,
                "trust": current_trust,
                "contradictions": contradictions,
                "timestamp": datetime.utcnow().isoformat(),
                "reviewed": False
            }
            self.history.append(entry)
            self._save()

        # تعلم من التناقضات السابقة
        past = [h for h in self.history if h.get("key") == key]
        recurring = len(past) > 2

        ctx.add_result("contradiction", {
            "has_contradictions": len(contradictions) > 0,
            "is_duplicate": duplicate,
            "recurring_issues": recurring,
            "past_count": len(past)
        })
        return ctx
