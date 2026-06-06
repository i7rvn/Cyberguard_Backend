"""Layer 11: Learning — Neural Network + Memory Storage"""
import numpy as np, json, os
from layers.base import BaseLayer
from engine.context import AnalysisContext
from config import settings
from datetime import datetime

WEIGHTS_FILE = "data/training/neural_weights.json"

class LearningLayer(BaseLayer):
    name = "layer11_learning"
    critical = False
    weight = 1.2

    def __init__(self):
        self.weights = self._load_weights()

    def _load_weights(self):
        if os.path.exists(WEIGHTS_FILE):
            try:
                with open(WEIGHTS_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_weights(self):
        os.makedirs("data/training", exist_ok=True)
        with open(WEIGHTS_FILE, "w") as f:
            json.dump(self.weights, f, indent=2)

    async def process(self, ctx: AnalysisContext) -> AnalysisContext:
        tool = ctx.tool
        fv   = ctx.feature_vector

        if not fv:
            ctx.add_result("learning", {"prediction": 0.5, "trained": False})
            return ctx

        prediction = self.predict(tool, fv)
        ctx.add_result("learning", {"prediction": prediction, "trained": True})
        ctx.add_vote("learning", prediction, weight=1.2)
        return ctx

    def predict(self, tool: str, fv: list) -> float:
        w = self.weights.get(tool, {})
        if not w.get("w1"):
            return 0.5
        try:
            x  = np.array(fv, dtype=float)
            w1 = np.array(w["w1"])
            w2 = np.array(w["w2"])
            b1 = np.array(w["b1"])
            b2 = np.array(w["b2"])
            h  = np.tanh(x @ w1 + b1)
            out = 1 / (1 + np.exp(-(h @ w2 + b2)))
            return float(np.clip(out[0], 0.0, 1.0))
        except Exception:
            return 0.5

    def update(self, tool: str, fv: list, expected: float, lr: float = 0.01):
        if not fv:
            return
        w = self.weights.get(tool, {})
        n_in = len(fv)
        n_hid = 10
        if not w.get("w1"):
            self.weights[tool] = {
                "w1": (np.random.randn(n_in, n_hid) * 0.1).tolist(),
                "w2": (np.random.randn(n_hid, 1) * 0.1).tolist(),
                "b1": np.zeros(n_hid).tolist(),
                "b2": [0.0],
                "accuracy": 0.75
            }
            w = self.weights[tool]
        try:
            x  = np.array(fv, dtype=float)
            w1 = np.array(w["w1"]); w2 = np.array(w["w2"])
            b1 = np.array(w["b1"]); b2 = np.array(w["b2"])
            h   = np.tanh(x @ w1 + b1)
            out = 1 / (1 + np.exp(-(h @ w2 + b2)))
            err = expected - out[0]
            d2  = err * out[0] * (1 - out[0])
            d1  = (d2 * w2.T) * (1 - h**2)
            self.weights[tool]["w2"] = (w2 + lr * h.reshape(-1,1) * d2).tolist()
            self.weights[tool]["w1"] = (w1 + lr * np.outer(x, d1)).tolist()
            self.weights[tool]["b2"] = (b2 + lr * d2).tolist()
            self.weights[tool]["b1"] = (b1 + lr * d1.flatten()).tolist()
            self._save_weights()
        except Exception as e:
            pass
