"""Layer 2: Verifier — التحقق + Source Reputation + Multi-Source Consensus"""
from layers.base import BaseLayer
from engine.context import AnalysisContext

SOURCE_REPUTATION = {
    "nvd.nist.gov": 100, "cve.mitre.org": 100,
    "gov": 95, "github.com": 90, "wikipedia.org": 85,
    "microsoft.com": 90, "google.com": 88,
    "owasp.org": 95, "sans.org": 90,
}

class VerifierLayer(BaseLayer):
    name = "layer02_verifier"
    critical = True
    weight = 1.5

    async def process(self, ctx: AnalysisContext) -> AnalysisContext:
        items = ctx.results.get("collector", {}).get("items", [])
        if not items:
            ctx.add_result("verifier", {"score": 0.3, "sources": 0,
                                        "consensus": False, "verified": False})
            ctx.confidence["source_score"] = 15.0
            return ctx

        keywords = self._keywords(ctx.input_data)
        scored = []
        for item in items:
            text = (item.get("title","") + " " + item.get("snippet","")).lower()
            kw_match = sum(1 for k in keywords if k in text) / max(len(keywords),1)
            rep = self._reputation(item.get("source",""))
            item_score = kw_match * 0.6 + (rep/100) * 0.4
            scored.append(item_score)
            # Remove sandbox flag after verification
            item["sandbox"] = False
            item["trust"] = round(item_score, 3)
            item["reputation"] = rep

        avg = sum(scored) / len(scored) if scored else 0.0
        # Multi-Source Consensus: 3+ مصادر متفقة = ثقة عالية
        consensus = len([s for s in scored if s > 0.5]) >= 3
        source_score = min(40.0, avg * 40 + (10 if consensus else 0))

        ctx.add_result("verifier", {
            "score": round(avg, 3),
            "sources": len(items),
            "consensus": consensus,
            "verified": avg > 0.3,
            "items": items
        })
        ctx.confidence["source_score"] = round(source_score, 2)
        ctx.add_vote("verifier", avg, weight=1.5)
        return ctx

    def _keywords(self, text: str) -> list:
        stop = {"is","the","a","an","of","to","in","and","or","for","with","this"}
        return [w for w in text.lower().split() if w not in stop and len(w) > 3][:12]

    def _reputation(self, source: str) -> int:
        for k, v in SOURCE_REPUTATION.items():
            if k in source:
                return v
        return 30
