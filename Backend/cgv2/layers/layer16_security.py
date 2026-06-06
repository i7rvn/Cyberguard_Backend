"""Layer 16: Security — Advanced Rate Limit + Safety Core"""
from layers.base import BaseLayer
from engine.context import AnalysisContext
from config import settings
from utils.security import sanitize_input

PROTECTED = ["neural_weights","trust_scores","reputation","layer"]
ADMIN_ACTIONS = ["train","reset","ban","delete_knowledge"]

class SecurityLayer(BaseLayer):
    name = "layer16_security"
    critical = True
    weight = 2.0

    async def process(self, ctx: AnalysisContext) -> AnalysisContext:
        san = sanitize_input(ctx.input_data)
        if not san["safe"]:
            raise Exception(f"Unsafe input: {san['reason']}")
        ctx.input_data = san["cleaned"]

        for p in PROTECTED:
            if p in ctx.input_data.lower():
                raise Exception(f"Protected content referenced: {p}")

        manip = ctx.results.get("manipulation", {})
        if manip.get("is_spam"):
            raise Exception("Spam detected — request blocked")

        ctx.add_result("security", {"passed": True, "sanitized": True})
        return ctx
