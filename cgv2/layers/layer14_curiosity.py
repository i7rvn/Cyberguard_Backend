"""Layer 14: Curiosity — Cell Specialization Score"""
from layers.base import BaseLayer
from engine.context import AnalysisContext
from db.mongodb import get_db

class CuriosityLayer(BaseLayer):
    name = "layer14_curiosity"
    critical = False
    weight = 0.5

    KNOWN = {"phishing","malware","sql_injection","xss","brute_force",
             "ransomware","ddos","social_engineering","zero_day","csrf"}

    async def process(self, ctx: AnalysisContext) -> AnalysisContext:
        words = ctx.input_data.lower().split()
        unknown = [w for w in words
                   if len(w) > 6 and any(s in w for s in ["_attack","_vuln","_exploit"])
                   and w not in self.KNOWN]

        db = get_db()
        cell = await db.cells.find_one({"tool": ctx.tool}) or {}
        spec_score = cell.get("specialization", 0.7)

        ctx.add_result("curiosity", {
            "unknown_concepts": unknown[:3],
            "cell_specialization": spec_score
        })
        return ctx
