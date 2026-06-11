"""
Reward / Punishment System — مكافأة وعقاب متعدد المصادر
"""
from datetime import datetime
from visualization.ws_events import emit_event

class RewardSystem:
    def __init__(self, db, cell_manager):
        self.db           = db
        self.cell_manager = cell_manager

    async def reward(self, cell_type: str, source: str,
                     amount: float = 1.0, reason: str = ""):
        """مكافأة — يزيد سمعة الخلية وثقتها"""
        await self.db.cells.update_one(
            {"cell_type": cell_type},
            {
                "$inc": {"reputation": amount, "experience": 0.01},
                "$set": {"last_active": datetime.utcnow().isoformat()}
            }
        )
        await self._log(cell_type, "reward", source, amount, reason)
        await emit_event("CONFIDENCE_UPDATED", {
            "cell_type": cell_type,
            "change":    f"+{amount}",
            "source":    source,
            "reason":    reason,
        })

    async def punish(self, cell_type: str, source: str,
                      amount: float = 1.0, reason: str = ""):
        """عقاب — ينقص سمعة الخلية"""
        await self.db.cells.update_one(
            {"cell_type": cell_type},
            {"$inc": {"reputation": -amount}}
        )
        await self._log(cell_type, "punishment", source, -amount, reason)
        await emit_event("CONFIDENCE_UPDATED", {
            "cell_type": cell_type,
            "change":    f"-{amount}",
            "source":    source,
            "reason":    reason,
        })

    async def evaluate(self, cell_type: str, prediction: float,
                        actual: bool, scan_result: dict = None,
                        vt_confirmed: bool = False,
                        human_rating: str = None) -> dict:
        """تقييم شامل من كل المصادر"""
        rewards   = []
        punishments = []

        # 1. Verification Success
        correct = (prediction > 0.5) == actual
        if correct:
            await self.reward(cell_type, "verification", 2.0, "Correct prediction")
            rewards.append("verification_success")
        else:
            await self.punish(cell_type, "verification", 1.5, "Wrong prediction")
            punishments.append("prediction_wrong")

        # 2. VirusTotal Confirmation
        if vt_confirmed and actual:
            await self.reward(cell_type, "virustotal", 3.0, "VT confirmed threat")
            rewards.append("virustotal_confirmed")

        # 3. Human Feedback
        if human_rating == "like":
            await self.reward(cell_type, "human", 1.0, "User confirmed")
            rewards.append("human_positive")
        elif human_rating == "dislike":
            await self.punish(cell_type, "human", 0.8, "User rejected")
            punishments.append("false_positive" if not actual else "false_negative")

        # 4. Consensus Between Sources
        if scan_result:
            sources_count = scan_result.get("sources_checked", 0)
            if sources_count >= 3:
                await self.reward(cell_type, "consensus", 1.5, "Multi-source consensus")
                rewards.append("consensus_reached")

        return {
            "rewards":      rewards,
            "punishments":  punishments,
            "net_score":    len(rewards) * 1.5 - len(punishments),
        }

    async def _log(self, cell_type: str, event_type: str,
                   source: str, amount: float, reason: str):
        await self.db.reward_logs.insert_one({
            "cell_type":  cell_type,
            "event_type": event_type,
            "source":     source,
            "amount":     amount,
            "reason":     reason,
            "timestamp":  datetime.utcnow().isoformat(),
        })
