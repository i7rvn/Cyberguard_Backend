"""
Discovery Engine — الاستنتاج وبناء معرفة جديدة
"""
from datetime import datetime
from visualization.ws_events import emit_event

# علاقات الاستنتاج المعروفة
INFERENCE_RULES = [
    {
        "if":   ["rain", "soil_moisture"],
        "then": "plant_growth",
        "confidence": 0.85,
        "label": "Rain helps plant growth",
    },
    {
        "if":   ["malware", "network_traffic"],
        "then": "data_exfiltration",
        "confidence": 0.80,
        "label": "Malware may cause data exfiltration",
    },
    {
        "if":   ["phishing", "credential"],
        "then": "account_compromise",
        "confidence": 0.90,
        "label": "Phishing leads to account compromise",
    },
    {
        "if":   ["ransomware", "encryption"],
        "then": "data_loss",
        "confidence": 0.95,
        "label": "Ransomware causes data loss",
    },
    {
        "if":   ["sql_injection", "database"],
        "then": "data_breach",
        "confidence": 0.88,
        "label": "SQL Injection leads to data breach",
    },
    {
        "if":   ["vulnerability", "exploit"],
        "then": "system_compromise",
        "confidence": 0.85,
        "label": "Exploited vulnerability → system compromise",
    },
    {
        "if":   ["xss", "session"],
        "then": "session_hijacking",
        "confidence": 0.82,
        "label": "XSS can lead to session hijacking",
    },
    {
        "if":   ["ddos", "availability"],
        "then": "service_disruption",
        "confidence": 0.92,
        "label": "DDoS causes service disruption",
    },
]

class DiscoveryEngine:
    def __init__(self, db):
        self.db = db

    async def discover(self, known_concepts: set, cell_type: str) -> list[dict]:
        """استنتج معرفة جديدة من المفاهيم المعروفة"""
        discoveries = []

        for rule in INFERENCE_RULES:
            conditions = set(rule["if"])
            if conditions.issubset(known_concepts):
                conclusion = rule["then"]

                # هل هذا الاستنتاج موجود؟
                existing = await self.db.hypotheses.find_one({
                    "conclusion": conclusion, "status": "confirmed"
                })
                if existing:
                    continue

                discovery = {
                    "type":       "inference",
                    "conditions": rule["if"],
                    "conclusion": conclusion,
                    "label":      rule["label"],
                    "confidence": rule["confidence"],
                    "cell_type":  cell_type,
                    "discovered_at": datetime.utcnow().isoformat(),
                    "status":     "hypothesis",
                }

                await self.db.hypotheses.update_one(
                    {"conclusion": conclusion},
                    {"$setOnInsert": discovery},
                    upsert=True
                )

                discoveries.append(discovery)

                await emit_event("DISCOVERY_MADE", {
                    "label":      rule["label"],
                    "confidence": rule["confidence"],
                    "conclusion": conclusion,
                })

        return discoveries

    async def validate_hypothesis(self, conclusion: str,
                                   evidence: dict) -> bool:
        """تحقق من فرضية بناءً على أدلة جديدة"""
        hypo = await self.db.hypotheses.find_one({"conclusion": conclusion})
        if not hypo:
            return False

        confidence = hypo.get("confidence", 0.5)
        # إذا جاء دليل جديد — زد الثقة
        if evidence.get("confirms"):
            confidence = min(1.0, confidence + 0.1)
        else:
            confidence = max(0.0, confidence - 0.15)

        new_status = "confirmed" if confidence >= 0.75 else \
                     "rejected"  if confidence < 0.3  else "hypothesis"

        await self.db.hypotheses.update_one(
            {"conclusion": conclusion},
            {"$set": {
                "confidence":  confidence,
                "status":      new_status,
                "validated_at":datetime.utcnow().isoformat(),
            }}
        )

        if new_status == "confirmed":
            await emit_event("DISCOVERY_MADE", {
                "label":      f"Confirmed: {conclusion}",
                "confidence": confidence,
                "validated":  True,
            })

        return new_status == "confirmed"

    async def extract_concepts(self, text: str) -> set:
        """استخرج المفاهيم من النص"""
        CONCEPTS = {
            "malware", "network", "phishing", "email", "ransomware",
            "encryption", "vulnerability", "sql_injection", "database",
            "xss", "session", "ddos", "availability", "exploit",
            "credential", "network_traffic", "data_exfiltration",
            "rain", "soil_moisture", "plant_growth",
        }
        text_lower = text.lower()
        return {c for c in CONCEPTS if c.replace("_"," ") in text_lower or c in text_lower}

    async def get_all_hypotheses(self) -> list:
        return await self.db.hypotheses.find({}).to_list(200)
