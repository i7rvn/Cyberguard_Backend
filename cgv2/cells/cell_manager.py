"""
Cell Manager — إنشاء وإدارة وتطور الخلايا
"""
import asyncio
from datetime import datetime
from cells.cell_model import KnowledgeCell, EVOLUTION_MAP, CELL_TYPES
from visualization.ws_events import emit_event

class CellManager:
    def __init__(self, db):
        self.db = db
        self._cells_cache: dict = {}

    async def init_root_cells(self):
        """أنشئ الخلايا الجذرية إذا ما موجودة"""
        existing = await self.db.cells.count_documents({})
        if existing > 0:
            return

        root_types = ["security", "malware", "vulnerability",
                      "network", "threat_intelligence"]
        for ct in root_types:
            cell = KnowledgeCell(
                name=f"{ct.replace('_',' ').title()} Cell",
                cell_type=ct,
                confidence=0.6,
                reputation=50.0,
            )
            await self.db.cells.insert_one(cell.to_dict())
            await emit_event("CELL_CREATED", {
                "cell_id": cell.cell_id,
                "name":    cell.name,
                "type":    cell.cell_type,
            })

    async def get_cell(self, cell_type: str) -> KnowledgeCell | None:
        doc = await self.db.cells.find_one({"cell_type": cell_type, "is_retired": False})
        return KnowledgeCell.from_dict(doc) if doc else None

    async def get_all_cells(self) -> list[KnowledgeCell]:
        docs = await self.db.cells.find({"is_retired": False}).to_list(200)
        return [KnowledgeCell.from_dict(d) for d in docs]

    async def add_knowledge_to_cell(self, cell_type: str,
                                     knowledge_item: dict) -> KnowledgeCell:
        """أضف معرفة لخلية وتحقق من الحاجة للتطور"""
        cell = await self.get_cell(cell_type)
        if not cell:
            cell = await self.create_cell(cell_type)

        # تحديث الخلية
        cell.knowledge_count += 1
        cell.experience       = min(1.0, cell.experience + 0.001)
        cell.last_active      = datetime.utcnow()
        cell.specialization   = min(1.0, cell.specialization + 0.002)

        await self.db.cells.update_one(
            {"cell_id": cell.cell_id},
            {"$set": {
                "knowledge_count": cell.knowledge_count,
                "experience":      cell.experience,
                "last_active":     cell.last_active.isoformat(),
                "specialization":  cell.specialization,
            }}
        )

        await emit_event("KNOWLEDGE_ADDED", {
            "cell_id":        cell.cell_id,
            "cell_name":      cell.name,
            "knowledge_count":cell.knowledge_count,
            "topic":          knowledge_item.get("title","")[:60],
        })

        # فحص التطور
        threshold = CELL_TYPES.get(cell_type, {}).get("threshold", 100)
        if cell.knowledge_count >= threshold and cell_type in EVOLUTION_MAP:
            await self.evolve_cell(cell)

        return cell

    async def evolve_cell(self, parent: KnowledgeCell):
        """تفرع الخلية إلى خلايا متخصصة"""
        children = EVOLUTION_MAP.get(parent.cell_type, [])
        for child_type in children:
            existing = await self.get_cell(child_type)
            if existing:
                continue
            child = await self.create_cell(child_type, parent_id=parent.cell_id)
            # أضف رابط بين الأب والابن
            await self.add_connection(parent.cell_id, child.cell_id, "evolved_to")

        parent.evolution_count += 1
        await self.db.cells.update_one(
            {"cell_id": parent.cell_id},
            {"$set": {"evolution_count": parent.evolution_count}}
        )

        await emit_event("CELL_SPECIALIZED", {
            "parent_id":   parent.cell_id,
            "parent_name": parent.name,
            "children":    children,
        })

    async def create_cell(self, cell_type: str,
                           parent_id: str = None) -> KnowledgeCell:
        cell = KnowledgeCell(
            name=f"{cell_type.replace('_',' ').title()} Cell",
            cell_type=cell_type,
            parent_id=parent_id,
            confidence=0.5,
            reputation=40.0,
        )
        await self.db.cells.insert_one(cell.to_dict())
        await emit_event("CELL_CREATED", {
            "cell_id":   cell.cell_id,
            "name":      cell.name,
            "type":      cell.cell_type,
            "parent_id": parent_id,
        })
        return cell

    async def add_connection(self, from_id: str, to_id: str,
                              relation: str = "connected"):
        await self.db.cells.update_one(
            {"cell_id": from_id},
            {"$addToSet": {"connections": {"to": to_id, "relation": relation}}}
        )
        await emit_event("CONNECTION_CREATED", {
            "from": from_id, "to": to_id, "relation": relation
        })

    async def update_reputation(self, cell_type: str, reward: bool):
        delta = +2.0 if reward else -1.5
        await self.db.cells.update_one(
            {"cell_type": cell_type},
            {"$inc": {"reputation": delta}}
        )
        cell = await self.get_cell(cell_type)
        if cell:
            await emit_event("CONFIDENCE_UPDATED", {
                "cell_id":    cell.cell_id,
                "reputation": cell.reputation,
                "rewarded":   reward,
            })

    async def dynamic_cell_creation(self, topic: str):
        """إنشاء خلية جديدة تلقائياً عند تراكم معرفة كافية"""
        count = await self.db.knowledge.count_documents({"topic": topic})
        if count >= 50:
            existing = await self.db.cells.find_one({"cell_type": topic})
            if not existing:
                cell = KnowledgeCell(
                    name=f"{topic.replace('_',' ').title()} Cell",
                    cell_type=topic,
                    confidence=0.5,
                    reputation=30.0,
                )
                await self.db.cells.insert_one(cell.to_dict())
                await emit_event("CELL_CREATED", {
                    "cell_id": cell.cell_id,
                    "name":    cell.name,
                    "auto":    True,
                })

    async def retire_weak_cells(self):
        """تقاعد الخلايا الضعيفة"""
        weak = await self.db.cells.find({
            "reputation": {"$lt": 10},
            "knowledge_count": {"$lt": 5},
            "is_retired": False
        }).to_list(20)

        for doc in weak:
            await self.db.cells.update_one(
                {"cell_id": doc["cell_id"]},
                {"$set": {"is_retired": True, "is_active": False}}
            )
            await emit_event("CELL_RETIRED", {
                "cell_id": doc["cell_id"],
                "name":    doc.get("name",""),
                "reason":  "low_reputation",
            })
