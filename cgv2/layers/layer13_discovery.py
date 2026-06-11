"""Layer 13: Discovery — Knowledge Graph + Threat Correlation"""
from layers.base import BaseLayer
from engine.context import AnalysisContext
import json, os

GRAPH_FILE  = "data/knowledge/knowledge_graph.json"
RELATIONS = {
    "phishing":       ["malicious_links","spam","social_engineering"],
    "sql_injection":  ["database","web_security","input_validation"],
    "xss":            ["javascript","html","web_security"],
    "malware":        ["virus","ransomware","trojan"],
    "brute_force":    ["password","authentication","rate_limiting"],
    "malicious_links":["phishing","malware","spam"],
}

class DiscoveryLayer(BaseLayer):
    name = "layer13_discovery"
    critical = False
    weight = 0.7

    def __init__(self):
        self.graph = self._load()

    def _load(self):
        if os.path.exists(GRAPH_FILE):
            try:
                with open(GRAPH_FILE) as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    async def process(self, ctx: AnalysisContext) -> AnalysisContext:
        tool = ctx.tool
        threat = ctx.threat_level

        related = RELATIONS.get(tool, [])
        learned = self.graph.get(tool, [])
        all_related = list(set(related + learned))

        inferences = self._infer(tool, threat)
        ctx.inferences.extend(inferences)

        # Threat Correlation
        correlations = self._correlate(ctx)

        ctx.add_result("discovery", {
            "related_concepts": all_related,
            "inferences": inferences,
            "correlations": correlations
        })
        return ctx

    def _infer(self, tool: str, threat: int) -> list:
        if threat < 40:
            return []
        inferences = {
            "malicious_links": ["Check related domains","Scan email sources"],
            "sql_injection":   ["Review input validation","Check DB permissions"],
            "xss":             ["Implement CSP headers","Check cookie security"],
            "malware":         ["Isolate system","Check lateral movement"],
            "phishing":        ["Warn users","Report to email provider"],
        }
        return inferences.get(tool, ["Review security settings"])[:2]

    def _correlate(self, ctx: AnalysisContext) -> list:
        correlations = []
        data = ctx.input_data.lower()
        import re
        ips = re.findall(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', data)
        domains = re.findall(r'[a-z0-9\-]+\.[a-z]{2,}', data)
        hashes  = re.findall(r'[a-f0-9]{32,64}', data)
        if ips:      correlations.append({"type": "ip",     "values": ips[:3]})
        if domains:  correlations.append({"type": "domain", "values": domains[:3]})
        if hashes:   correlations.append({"type": "hash",   "values": hashes[:2]})
        return correlations
