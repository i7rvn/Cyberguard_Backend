"""Layer 15: Explainability — Explainable Everything"""
from layers.base import BaseLayer
from engine.context import AnalysisContext

RECS = {
    "malicious_links": ["Do not visit this URL","Report to Safe Browsing"],
    "phishing":        ["Do not click any links","Report to email provider"],
    "sql_injection":   ["Use parameterized queries","Validate all inputs"],
    "xss":             ["Implement CSP","Sanitize user inputs"],
    "password_strength":["Use 12+ characters","Enable 2FA"],
    "malware":         ["Do not execute","Isolate system immediately"],
    "brute_force":     ["Implement rate limiting","Enable account lockout"],
}

class ExplainabilityLayer(BaseLayer):
    name = "layer15_explainability"
    critical = False
    weight = 0.6

    async def process(self, ctx: AnalysisContext) -> AnalysisContext:
        vote   = ctx.get_weighted_vote()
        threat = int(vote * 100)
        conf   = ctx.confidence

        # Explainable scoring breakdown
        score_breakdown = []
        logic = ctx.results.get("logic", {})
        if logic.get("contradictions"):
            for c in logic["contradictions"][:3]:
                score_breakdown.append({"reason": c, "impact": "+20"})
        if logic.get("safe_override"):
            score_breakdown.append({"reason": "Known safe domain", "impact": "-60"})
        verif = ctx.results.get("verifier", {})
        if verif.get("consensus"):
            score_breakdown.append({"reason": "Multi-source consensus", "impact": "+10"})

        verdict = ("🚨 Very Dangerous" if threat >= 80 else
                   "⚠️ Dangerous"      if threat >= 60 else
                   "⚠️ Suspicious"     if threat >= 40 else
                   "✅ Safe")

        verdict_ar = ("خطر جداً" if threat >= 80 else
                      "خطر"       if threat >= 60 else
                      "مشبوه"     if threat >= 40 else
                      "آمن")

        ctx.explanation = {
            "verdict_en":       verdict,
            "verdict_ar":       verdict_ar,
            "threat_level":     threat,
            "confidence":       conf,
            "score_breakdown":  score_breakdown,
            "reasons":          [s["reason"] for s in score_breakdown],
            "recommendations":  RECS.get(ctx.tool, ["Review security settings"]),
            "inferences":       ctx.inferences[:3],
            "layer_votes":      ctx.layer_votes,
            "bypassed_layers":  ctx.bypassed_layers,
        }
        ctx.threat_level = threat
        ctx.accuracy = round(
            (conf.get("source_score",0) + conf.get("human_score",0) +
             conf.get("experience_score",0) + conf.get("consensus_score",0)) / 100 * 100, 1)
        return ctx
