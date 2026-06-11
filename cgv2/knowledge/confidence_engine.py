"""
Confidence Engine — حساب الثقة من 5 مصادر
"""
from dataclasses import dataclass

@dataclass
class ConfidenceBreakdown:
    source_score:       float = 0.0
    consensus_score:    float = 0.0
    experience_score:   float = 0.0
    human_score:        float = 0.0
    verification_score: float = 0.0

    @property
    def final(self) -> float:
        raw = (
            self.source_score       * 0.30 +
            self.consensus_score    * 0.25 +
            self.experience_score   * 0.20 +
            self.human_score        * 0.10 +
            self.verification_score * 0.15
        )
        return round(min(1.0, max(0.0, raw)), 4)

    def to_dict(self) -> dict:
        return {
            "final":              round(self.final * 100, 2),
            "source_score":       round(self.source_score * 100, 2),
            "consensus_score":    round(self.consensus_score * 100, 2),
            "experience_score":   round(self.experience_score * 100, 2),
            "human_score":        round(self.human_score * 100, 2),
            "verification_score": round(self.verification_score * 100, 2),
        }

class ConfidenceEngine:
    def calculate(self,
                  sources:       list[dict],
                  search_results:list[dict],
                  cell_reputation: float,
                  human_ratings:   int,
                  verification_ok: bool,
                  scan_result:     dict = None) -> ConfidenceBreakdown:

        cb = ConfidenceBreakdown()

        # 1. Source Score — جودة المصادر
        SOURCE_REP = {
            "nvd.nist.gov": 1.0, "cve.mitre.org": 1.0,
            "cisa.gov": 0.98,    "owasp.org": 0.95,
            "github.com": 0.90,  "wikipedia.org": 0.85,
            "microsoft.com": 0.90,
        }
        if sources:
            scores = []
            for s in sources:
                src = s.get("source","").lower()
                rep = max((v for k,v in SOURCE_REP.items() if k in src), default=0.3)
                scores.append(rep)
            cb.source_score = sum(scores) / len(scores)

        # 2. Consensus Score — اتفاق المصادر
        if len(search_results) >= 3:
            cb.consensus_score = 0.8
        elif len(search_results) >= 2:
            cb.consensus_score = 0.5
        else:
            cb.consensus_score = 0.2

        # 3. Experience Score — سمعة الخلية
        cb.experience_score = min(1.0, cell_reputation / 100)

        # 4. Human Score — تقييمات البشر
        cb.human_score = min(1.0, human_ratings / 50)

        # 5. Verification Score — نتائج الفحص الفعلي
        if verification_ok:
            cb.verification_score = 0.9
        if scan_result:
            vt_confirmed = scan_result.get("virustotal_confirmed", False)
            if vt_confirmed:
                cb.verification_score = 1.0

        return cb
