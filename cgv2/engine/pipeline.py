"""Layer Pipeline — يشغّل الطبقات بالترتيب"""
from engine.context import AnalysisContext
from utils.logger import logger
import hashlib, time

from layers.layer01_collector     import CollectorLayer
from layers.layer02_verifier      import VerifierLayer
from layers.layer03_trust         import TrustLayer
from layers.layer04_logic         import LogicLayer
from layers.layer05_contradiction import ContradictionLayer
from layers.layer06_human         import HumanFeedbackLayer
from layers.layer07_reputation    import ReputationLayer
from layers.layer08_time          import TimeLayer
from layers.layer09_manipulation  import ManipulationLayer
from layers.layer10_experience    import ExperienceLayer
from layers.layer11_learning      import LearningLayer
from layers.layer12_forgetting    import ForgettingLayer
from layers.layer13_discovery     import DiscoveryLayer
from layers.layer14_curiosity     import CuriosityLayer
from layers.layer15_explainability import ExplainabilityLayer
from layers.layer16_security      import SecurityLayer
from layers.layer17_goals         import GoalsLayer
from utils.feature_extractor      import FeatureExtractor

features = FeatureExtractor()

# Singleton instances
_layers = [
    SecurityLayer(),      # L16 أول — أمان
    ManipulationLayer(),  # L9
    CollectorLayer(),     # L1
    VerifierLayer(),      # L2
    TrustLayer(),         # L3
    LogicLayer(),         # L4
    ContradictionLayer(), # L5
    ReputationLayer(),    # L7
    HumanFeedbackLayer(), # L6
    TimeLayer(),          # L8
    ExperienceLayer(),    # L10
    LearningLayer(),      # L11
    ForgettingLayer(),    # L12
    DiscoveryLayer(),     # L13
    CuriosityLayer(),     # L14
    ExplainabilityLayer(),# L15
    GoalsLayer(),         # L17
]

_trust_layer   = _layers[4]
_learning_layer = _layers[11]

async def run_pipeline(tool: str, input_data: str,
                       user_id: int = 0, profile: str = "normal") -> AnalysisContext:
    key = hashlib.md5(f"{tool}:{input_data[:100]}".encode()).hexdigest()
    ctx = AnalysisContext(
        tool=tool, input_data=input_data,
        user_id=user_id, profile=profile, key=key,
        feature_vector=features.extract(tool, input_data)
    )

    for layer in _layers:
        try:
            ctx = await layer.run(ctx)
        except Exception as e:
            if layer.critical:
                logger.error("critical_layer_failed", layer=layer.name, error=str(e))
                ctx.explanation = {"verdict_ar": "خطأ في التحليل",
                                   "verdict_en": "Analysis Error",
                                   "threat_level": 0, "error": str(e)}
                return ctx

    logger.info("pipeline_complete", tool=tool, threat=ctx.threat_level,
                elapsed_ms=ctx.elapsed_ms(), key=key[:8])
    return ctx

def get_trust_layer() -> TrustLayer:
    return _trust_layer

def get_learning_layer() -> LearningLayer:
    return _learning_layer
