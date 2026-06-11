"""
Knowledge Graph — شبكة العلاقات بين المعرفة
"""
from datetime import datetime
from visualization.ws_events import emit_event

class KnowledgeGraph:
    def __init__(self, db):
        self.db = db

    async def add_node(self, key: str, data: dict, cell_type: str) -> dict:
        """أضف عقدة معرفة جديدة"""
        node = {
            "key":       key,
            "title":     data.get("title", "")[:200],
            "snippet":   data.get("snippet", "")[:500],
            "source":    data.get("source", ""),
            "cell_type": cell_type,
            "topic":     data.get("topic", cell_type),
            "confidence":data.get("confidence", 0.5),
            "sandbox":   True,   # تدخل الـ Sandbox أولاً
            "verified":  False,
            "created_at":datetime.utcnow().isoformat(),
            "relations": [],
        }
        await self.db.knowledge.update_one(
            {"key": key}, {"$setOnInsert": node}, upsert=True
        )
        return node

    async def verify_node(self, key: str, confidence: float):
        """نقل من Sandbox للمعرفة الحقيقية بعد التحقق"""
        if confidence >= 0.5:
            await self.db.knowledge.update_one(
                {"key": key},
                {"$set": {"sandbox": False, "verified": True,
                          "confidence": confidence,
                          "verified_at": datetime.utcnow().isoformat()}}
            )

    async def add_relation(self, key_a: str, key_b: str,
                            relation: str, strength: float = 0.5):
        """أضف علاقة بين عقدتين"""
        rel = {"to": key_b, "relation": relation,
               "strength": strength, "created_at": datetime.utcnow().isoformat()}

        await self.db.knowledge.update_one(
            {"key": key_a},
            {"$addToSet": {"relations": rel}}
        )
        await emit_event("CONNECTION_CREATED", {
            "from": key_a, "to": key_b,
            "relation": relation, "strength": strength
        })

    async def extract_relations(self, items: list[dict],
                                 cell_type: str) -> list[dict]:
        """استخرج العلاقات تلقائياً من المعرفة"""
        relations = []
        keywords = self._extract_keywords(items)

        KNOWN_RELATIONS = {
            ("malware","network"):     "spreads_through",
            ("phishing","email"):      "delivered_via",
            ("ransomware","encryption"):"uses",
            ("cve","vulnerability"):   "is_a",
            ("sql_injection","database"):"targets",
            ("xss","javascript"):      "exploits",
            ("ddos","network"):        "attacks",
        }

        for (a, b), rel in KNOWN_RELATIONS.items():
            if a in keywords and b in keywords:
                relations.append({"from": a, "to": b, "relation": rel})
                await self.add_relation(
                    f"{cell_type}:{a}", f"{cell_type}:{b}", rel, 0.7
                )

        return relations

    def _extract_keywords(self, items: list[dict]) -> set:
        SECURITY_TERMS = {
            "malware","network","phishing","email","ransomware",
            "encryption","cve","vulnerability","sql_injection",
            "database","xss","javascript","ddos","trojan",
            "worm","firewall","exploit","backdoor","rootkit",
        }
        found = set()
        for item in items:
            text = (item.get("title","") + " " + item.get("snippet","")).lower()
            for term in SECURITY_TERMS:
                if term in text:
                    found.add(term)
        return found

    async def get_graph_data(self) -> dict:
        """جلب بيانات الرسم البياني للـ Frontend"""
        nodes = await self.db.knowledge.find(
            {"verified": True},
            {"key":1,"title":1,"cell_type":1,"confidence":1,"relations":1}
        ).limit(500).to_list(500)

        edges = []
        for node in nodes:
            for rel in node.get("relations", []):
                edges.append({
                    "from": node["key"],
                    "to":   rel["to"],
                    "relation": rel.get("relation",""),
                    "strength": rel.get("strength", 0.5),
                })

        return {"nodes": len(nodes), "edges": len(edges), "data": nodes[:100]}
