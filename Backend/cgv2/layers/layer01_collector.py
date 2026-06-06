"""Layer 1: Collector — جمع المعلومات + Trust Sandbox"""
import httpx
from layers.base import BaseLayer
from engine.context import AnalysisContext
from config import settings

TOOL_QUERIES = {
    "malicious_links":  "is this URL safe malicious check: {d}",
    "phishing":         "phishing detection analysis: {d}",
    "sql_injection":    "SQL injection vulnerability: {d}",
    "xss":              "XSS cross-site scripting: {d}",
    "password_strength":"password security analysis",
    "malware":          "malware code detection: {d}",
    "brute_force":      "brute force attack detection",
    "python_vuln":      "python security vulnerability: {d}",
    "js_vuln":          "javascript security vulnerability: {d}",
}

class CollectorLayer(BaseLayer):
    name = "layer01_collector"
    critical = False
    weight = 0.8

    async def process(self, ctx: AnalysisContext) -> AnalysisContext:
        results = []
        d = ctx.input_data[:80]
        q = TOOL_QUERIES.get(ctx.tool, f"cybersecurity {ctx.tool}: {d}")
        query = q.format(d=d)

        # Google Custom Search
        if settings.GOOGLE_API_KEY and settings.GOOGLE_CX:
            results += await self._google_search(query)

        # Wikipedia
        results += await self._wikipedia(query[:50])

        # CVE Database
        if "vuln" in ctx.tool or "injection" in ctx.tool or "xss" in ctx.tool:
            results += await self._cve_search(ctx.tool)

        # Trust Sandbox: mark as unverified
        sandboxed = [{"source": r["source"], "title": r["title"],
                      "snippet": r["snippet"], "trust": 0.0,
                      "sandbox": True} for r in results]

        ctx.add_result("collector", {
            "raw_count": len(results),
            "items": sandboxed[:8],
            "query": query
        })
        return ctx

    async def _google_search(self, query: str) -> list:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {"key": settings.GOOGLE_API_KEY, "cx": settings.GOOGLE_CX,
                  "q": query, "num": 5}
        try:
            async with httpx.AsyncClient(timeout=8) as c:
                r = await c.get(url, params=params)
                items = r.json().get("items", [])
                return [{"title": i.get("title",""),
                         "snippet": i.get("snippet",""),
                         "source": i.get("displayLink","")} for i in items]
        except Exception:
            return []

    async def _wikipedia(self, query: str) -> list:
        url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + query.replace(" ","_")
        try:
            async with httpx.AsyncClient(timeout=6) as c:
                r = await c.get(url)
                if r.status_code == 200:
                    d = r.json()
                    return [{"title": d.get("title",""),
                             "snippet": d.get("extract","")[:300],
                             "source": "wikipedia.org"}]
        except Exception:
            pass
        return []

    async def _cve_search(self, tool: str) -> list:
        keyword = {"sql_injection":"sql+injection","xss":"cross+site+scripting",
                   "python_vuln":"python","js_vuln":"javascript"}.get(tool,"security")
        url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?keywordSearch={keyword}&resultsPerPage=3"
        try:
            async with httpx.AsyncClient(timeout=8) as c:
                r = await c.get(url)
                vulns = r.json().get("vulnerabilities",[])
                return [{"title": v["cve"]["id"],
                         "snippet": v["cve"].get("descriptions",[{}])[0].get("value","")[:200],
                         "source": "nvd.nist.gov"} for v in vulns]
        except Exception:
            return []
