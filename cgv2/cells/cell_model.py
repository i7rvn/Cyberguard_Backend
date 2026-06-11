"""
Knowledge Cell Model
كل خلية = وحدة معرفية متخصصة
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid

CELL_TYPES = {
    "security":            {"parent": None,       "threshold": 100},
    "malware":             {"parent": "security",  "threshold": 80},
    "vulnerability":       {"parent": "security",  "threshold": 80},
    "network":             {"parent": "security",  "threshold": 80},
    "threat_intelligence": {"parent": "security",  "threshold": 80},
    "trojan":              {"parent": "malware",   "threshold": 60},
    "ransomware":          {"parent": "malware",   "threshold": 60},
    "worm":                {"parent": "malware",   "threshold": 60},
    "spyware":             {"parent": "malware",   "threshold": 60},
    "cve":                 {"parent": "vulnerability", "threshold": 60},
    "zero_day":            {"parent": "vulnerability", "threshold": 60},
    "phishing":            {"parent": "threat_intelligence", "threshold": 60},
    "osint":               {"parent": "threat_intelligence", "threshold": 60},
    "ddos":                {"parent": "network",   "threshold": 60},
    "firewall":            {"parent": "network",   "threshold": 60},
}

# خريطة التفرع التلقائي
EVOLUTION_MAP = {
    "security": ["malware", "vulnerability", "network", "threat_intelligence"],
    "malware":  ["trojan", "ransomware", "worm", "spyware"],
    "vulnerability": ["cve", "zero_day"],
    "threat_intelligence": ["phishing", "osint"],
    "network": ["ddos", "firewall"],
}

@dataclass
class KnowledgeCell:
    cell_id:        str     = field(default_factory=lambda: str(uuid.uuid4())[:12])
    name:           str     = ""
    cell_type:      str     = "security"
    parent_id:      Optional[str] = None
    specialization: float   = 0.5
    knowledge_count:int     = 0
    confidence:     float   = 0.5
    experience:     float   = 0.0
    reputation:     float   = 50.0
    connections:    list    = field(default_factory=list)
    created_at:     datetime = field(default_factory=datetime.utcnow)
    last_active:    datetime = field(default_factory=datetime.utcnow)
    is_active:      bool    = True
    is_retired:     bool    = False
    evolution_count:int     = 0

    def to_dict(self) -> dict:
        return {
            "cell_id":        self.cell_id,
            "name":           self.name,
            "cell_type":      self.cell_type,
            "parent_id":      self.parent_id,
            "specialization": round(self.specialization, 4),
            "knowledge_count":self.knowledge_count,
            "confidence":     round(self.confidence, 4),
            "experience":     round(self.experience, 4),
            "reputation":     round(self.reputation, 2),
            "connections":    self.connections,
            "created_at":     self.created_at.isoformat(),
            "last_active":    self.last_active.isoformat(),
            "is_active":      self.is_active,
            "is_retired":     self.is_retired,
            "evolution_count":self.evolution_count,
        }

    @staticmethod
    def from_dict(d: dict) -> "KnowledgeCell":
        cell = KnowledgeCell()
        for k, v in d.items():
            if k in ("created_at", "last_active") and isinstance(v, str):
                setattr(cell, k, datetime.fromisoformat(v))
            elif hasattr(cell, k):
                setattr(cell, k, v)
        return cell
