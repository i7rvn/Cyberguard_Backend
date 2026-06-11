"""
Neural Knowledge Engine — المحرك الرئيسي الجديد
يجمع: Knowledge Graph + Cells + Discovery + Rewards + Neural Network
"""
import hashlib
from datetime import datetime

from cells.cell_manager      import CellManager
from knowledge.knowledge_graph import KnowledgeGraph
from knowledge.confidence_engine import ConfidenceEngine
from knowledge.sandbox       import KnowledgeSandbox
from discovery.discovery_engine import DiscoveryEngine
from rewards.reward_system   import RewardSystem
from visualization.ws_events import emit_event

class NeuralKnowledgeEngine:
    def __init__(self, db):
        self.db          = db
        self.cells       = CellManager(db)
        self.graph       = KnowledgeGraph(db)
        self.confidence  = ConfidenceEngine()
        self.sandbox     = KnowledgeSandbox(db)
        self.discovery   = DiscoveryEngine(db)
        self.rewards     = RewardSystem(db, self.cells)

    async def startup(self):
        """تهيئة عند بدء التشغيل"""
        await self.cells.init_root_cells()

    async def process(self, tool: str, input_data: str,
                      search_results: list, user_id: int = 0) -> dict:
        """
        دورة التعلم الكاملة:
        Collection → Verification → Confidence →
        Sandbox → Knowledge Graph → Cells →
        Cell Evolution → Discovery → Rewards
        """
        key = hashlib.md5(f"{tool}:{input_data[:80]}".encode()).hexdigest()

        # 1. تحديد نوع الخلية المناسبة
        cell_type = self._map_tool_to_cell(tool)
        cell = await self.cells.get_cell(cell_type)
        reputation = cell.reputation if cell else 50.0

        # 2. حساب الثقة
        cb = self.confidence.calculate(
            sources=search_results,
            search_results=search_results,
            cell_reputation=reputation,
            human_ratings=0,
            verification_ok=len(search_results) >= 2,
        )

        # 3. أدخل للـ Sandbox
        for i, item in enumerate(search_results[:5]):
            node_key = f"{key}:{i}"
            await self.sandbox.submit(node_key, item, cell_type, [item])
            sandbox_result = await self.sandbox.verify(
                node_key, reputation, 0, None
            )
            if sandbox_result["approved"]:
                # 4. أضف للـ Knowledge Graph
                await self.graph.add_node(node_key, item, cell_type)

                # 5. استخرج العلاقات
                await self.graph.extract_relations([item], cell_type)

        # 6. أضف للخلية
        if search_results:
            await self.cells.add_knowledge_to_cell(
                cell_type, search_results[0]
            )

        # 7. Discovery — اكتشاف معرفة جديدة
        all_text = " ".join(
            r.get("title","") + " " + r.get("snippet","")
            for r in search_results
        )
        concepts = await self.discovery.extract_concepts(all_text)
        discoveries = await self.discovery.discover(concepts, cell_type)

        # 8. تحقق من إنشاء خلايا ديناميكية
        for concept in concepts:
            await self.cells.dynamic_cell_creation(concept)

        return {
            "key":          key,
            "cell_type":    cell_type,
            "confidence":   cb.to_dict(),
            "knowledge_added": len(search_results),
            "discoveries":  len(discoveries),
            "concepts":     list(concepts),
        }

    async def feedback(self, key: str, tool: str,
                       rating: str, prediction: float = 0.5,
                       vt_confirmed: bool = False) -> dict:
        """معالجة تقييم المستخدم + مصادر أخرى"""
        cell_type = self._map_tool_to_cell(tool)
        actual    = rating == "like"

        result = await self.rewards.evaluate(
            cell_type=cell_type,
            prediction=prediction,
            actual=actual,
            human_rating=rating,
            vt_confirmed=vt_confirmed,
        )

        # تحديث الثقة في الـ sandbox
        await self.sandbox.verify(key, human_ratings=1 if actual else 0)

        return result

    async def train_weekly(self, neural_weights_updater) -> dict:
        """تدريب أسبوعي شامل"""
        # 1. تقاعد الخلايا الضعيفة
        await self.cells.retire_weak_cells()

        # 2. مراجعة الفرضيات
        hypotheses = await self.db.hypotheses.find(
            {"status": "hypothesis"}
        ).to_list(100)
        validated = 0
        for h in hypotheses:
            evidence = {"confirms": h.get("confidence", 0) > 0.6}
            ok = await self.discovery.validate_hypothesis(
                h["conclusion"], evidence
            )
            if ok: validated += 1

        return {
            "cells_retired": 0,
            "hypotheses_validated": validated,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _map_tool_to_cell(self, tool: str) -> str:
        MAPPING = {
            "malicious_links": "threat_intelligence",
            "phishing":        "phishing",
            "sql_injection":   "vulnerability",
            "xss":             "vulnerability",
            "malware":         "malware",
            "brute_force":     "network",
            "python_vuln":     "vulnerability",
            "js_vuln":         "vulnerability",
            "password_strength":"security",
            "hash_check":      "threat_intelligence",
        }
        return MAPPING.get(tool, "security")
