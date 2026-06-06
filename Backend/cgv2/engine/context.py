"""Analysis Context Object — يمر عبر كل الطبقات"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

@dataclass
class AnalysisContext:
    # Input
    input_data:   str = ""
    tool:         str = ""
    user_id:      int = 0
    profile:      str = "normal"

    # Generated
    key:          str = ""
    feature_vector: list = field(default_factory=list)

    # Results per layer
    results:      dict = field(default_factory=dict)

    # Confidence breakdown
    confidence: dict = field(default_factory=lambda: {
        "final":            0.0,
        "source_score":     0.0,
        "human_score":      0.0,
        "experience_score": 0.0,
        "consensus_score":  0.0,
    })

    # Voting
    layer_votes:  list  = field(default_factory=list)

    # Errors & bypasses
    errors:           list = field(default_factory=list)
    bypassed_layers:  list = field(default_factory=list)

    # Timing per layer
    processing_time:  dict = field(default_factory=dict)

    # Final output
    threat_level: int   = 0
    accuracy:     float = 0.0
    explanation:  dict  = field(default_factory=dict)
    inferences:   list  = field(default_factory=list)

    # Meta
    started_at:   datetime = field(default_factory=datetime.utcnow)
    safe_mode:    bool  = False
    sandbox_pass: bool  = False

    def add_result(self, layer: str, data: dict):
        self.results[layer] = data

    def add_vote(self, layer: str, vote: float, weight: float = 1.0):
        self.layer_votes.append({"layer": layer, "vote": vote, "weight": weight})

    def get_weighted_vote(self) -> float:
        if not self.layer_votes:
            return 0.5
        total_w = sum(v["weight"] for v in self.layer_votes)
        total_v = sum(v["vote"] * v["weight"] for v in self.layer_votes)
        return total_v / total_w if total_w > 0 else 0.5

    def elapsed_ms(self) -> float:
        return (datetime.utcnow() - self.started_at).total_seconds() * 1000
