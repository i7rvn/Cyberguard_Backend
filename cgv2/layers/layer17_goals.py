"""Layer 17: Goals — Scope Guard + Cross-Layer Final Vote"""
from layers.base import BaseLayer
from engine.context import AnalysisContext

ALLOWED_TOPICS = [
    "cybersecurity","malware","phishing","sql","xss","vulnerability",
    "network","password","encryption","firewall","intrusion",
    "authentication","exploit","attack","defense","forensics",
    "penetration","audit","ransomware","ddos","brute","injection",
]

class GoalsLayer(BaseLayer):
    name = "layer17_goals"
    critical = False
    weight = 1.0

    async def process(self, ctx: AnalysisContext) -> AnalysisContext:
        in_scope = any(t in ctx.tool.lower() or t in ctx.input_data.lower()[:200]
                       for t in ALLOWED_TOPICS)

        # Final Cross-Layer Vote
        final_vote = ctx.get_weighted_vote()

        if not in_scope:
            ctx.add_result("goals", {
                "in_scope": False, "final_vote": final_vote,
                "warning": "Topic may be outside scope"
            })
        else:
            ctx.add_result("goals", {"in_scope": True, "final_vote": final_vote})

        # Override threat_level با الـ vote النهائي إذا لم يُحسب بعد
        if ctx.threat_level == 0:
            logic = ctx.results.get("logic", {})
            if logic.get("safe_override"):
                ctx.threat_level = max(0, int(final_vote * 20))
            else:
                ctx.threat_level = int(final_vote * 100)
        return ctx
