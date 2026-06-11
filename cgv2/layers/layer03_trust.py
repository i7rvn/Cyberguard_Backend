"""Layer 3: Trust — Confidence Breakdown + Confidence Decay"""
import json, os
from datetime import datetime, timedelta
from layers.base import BaseLayer
from engine.context import AnalysisContext
from config import settings

TRUST_FILE = "data/knowledge/trust_scores.json"

class TrustLayer(BaseLayer):
    name = "layer03_trust"
    critical = True
    weight = 1.5

    def __init__(self):
        self.scores = self._load()

    def _load(self):
        if os.path.exists(TRUST_FILE):
            try:
                with open(TRUST_FILE) as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save(self):
        os.makedirs("data/knowledge", exist_ok=True)
        with open(TRUST_FILE, "w") as f:
            json.dump(self.scores, f, indent=2, ensure_ascii=False)

    async def process(self, ctx: AnalysisContext) -> AnalysisContext:
        key = ctx.key
        verif = ctx.results.get("verifier", {})
        source_score  = ctx.confidence.get("source_score", 0)
        human_score   = ctx.confidence.get("human_score", 0)
        exp_score     = ctx.confidence.get("experience_score", 0)
        consensus_score = 17.0 if verif.get("consensus") else 5.0

        # Confidence Decay — الثقة تنقص مع الوقت
        existing = self.scores.get(key, {})
        base_trust = existing.get("trust", 0.5)
        if existing:
            last = datetime.fromisoformat(existing.get("last_verified", datetime.utcnow().isoformat()))
            days_old = (datetime.utcnow() - last).days
            decay = max(0.0, days_old * 0.005)  # 0.5% يومياً
            base_trust = max(0.1, base_trust - decay)

        # احسب الثقة النهائية
        combined = (source_score + human_score + exp_score + consensus_score) / 100
        final_trust = base_trust * 0.3 + combined * 0.7
        final_trust = round(min(1.0, max(0.0, final_trust)), 4)

        final_pct = round(final_trust * 100, 2)
        ctx.confidence.update({
            "final":           final_pct,
            "consensus_score": round(consensus_score, 2),
        })

        self.scores[key] = {
            "trust": final_trust,
            "last_verified": datetime.utcnow().isoformat(),
            "sources": verif.get("sources", 0)
        }
        self._save()

        ctx.add_result("trust", {"trust": final_trust, "final_pct": final_pct})
        ctx.add_vote("trust", final_trust, weight=1.5)
        return ctx

    def update_human(self, key: str, rating: str, reputation: float = 1.0):
        delta = 0.05 * reputation if rating == "like" else -0.05 * reputation
        current = self.scores.get(key, {}).get("trust", 0.5)
        new_val = round(min(1.0, max(0.0, current + delta)), 4)
        if key not in self.scores:
            self.scores[key] = {}
        self.scores[key]["trust"] = new_val
        self._save()
