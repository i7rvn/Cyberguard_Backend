"""Layer 4: Logic — Known Facts Database"""
from layers.base import BaseLayer
from engine.context import AnalysisContext

KNOWN_FACTS = {
    "safe_domains": ["google.com","github.com","microsoft.com","apple.com",
                     "amazon.com","cloudflare.com","wikipedia.org","mozilla.org"],
    "dangerous_tlds": [".tk",".ml",".ga",".cf",".gq",".xyz",".top"],
    "sql_patterns": ["or 1=1","' or","--","union select","drop table",
                     "'; drop","xp_cmdshell","information_schema"],
    "xss_patterns": ["<script","javascript:","onerror=","onload=","alert(",
                     "document.cookie","eval(","<iframe"],
    "phishing_words": ["verify account","suspended","click here urgently",
                       "confirm password","bank alert","won prize",
                       "update payment","unauthorized access"],
}

class LogicLayer(BaseLayer):
    name = "layer04_logic"
    critical = False
    weight = 1.2

    async def process(self, ctx: AnalysisContext) -> AnalysisContext:
        data = ctx.input_data.lower()
        contradictions = []
        facts = []
        safe_override = False

        if ctx.tool == "malicious_links":
            for d in KNOWN_FACTS["safe_domains"]:
                if d in data:
                    facts.append(f"Known safe domain: {d}")
                    safe_override = True
                    break
            for tld in KNOWN_FACTS["dangerous_tlds"]:
                if tld in data:
                    contradictions.append(f"Dangerous TLD detected: {tld}")

        elif ctx.tool == "sql_injection":
            found = [k for k in KNOWN_FACTS["sql_patterns"] if k in data]
            if found:
                contradictions.append(f"SQL patterns found: {found}")

        elif ctx.tool == "xss":
            found = [k for k in KNOWN_FACTS["xss_patterns"] if k in data]
            if found:
                contradictions.append(f"XSS patterns found: {found}")

        elif ctx.tool == "phishing":
            found = [k for k in KNOWN_FACTS["phishing_words"] if k in data]
            if found:
                contradictions.append(f"Phishing keywords: {found}")

        ctx.add_result("logic", {
            "passed": len(contradictions) == 0,
            "contradictions": contradictions,
            "facts": facts,
            "safe_override": safe_override
        })

        vote = 0.1 if safe_override else (0.3 if contradictions else 0.7)
        ctx.add_vote("logic", vote, weight=1.2)
        return ctx
