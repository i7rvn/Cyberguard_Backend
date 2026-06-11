"""Layer 9: Manipulation Detection — Spam + Fake Accounts"""
from layers.base import BaseLayer
from engine.context import AnalysisContext
from collections import defaultdict
from datetime import datetime

_user_actions: dict = defaultdict(list)
_group_votes: dict  = defaultdict(list)

class ManipulationLayer(BaseLayer):
    name = "layer09_manipulation"
    critical = False
    weight = 1.0

    async def process(self, ctx: AnalysisContext) -> AnalysisContext:
        uid = ctx.user_id
        now = datetime.utcnow()
        _user_actions[uid].append(now)

        recent = [t for t in _user_actions[uid]
                  if (now - t).total_seconds() < 60]
        _user_actions[uid] = recent[-100:]

        is_spam = len(recent) > 25
        suspicious = len(recent) > 15

        fp_data = ctx.results.get("fingerprint", {})
        fp_suspicious = fp_data.get("suspicious", False)

        ctx.add_result("manipulation", {
            "is_spam": is_spam,
            "suspicious": suspicious or fp_suspicious,
            "actions_per_minute": len(recent),
            "fingerprint_suspicious": fp_suspicious
        })

        if is_spam:
            ctx.errors.append({"layer": self.name, "error": "Spam detected"})
        return ctx
