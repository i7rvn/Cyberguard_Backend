"""Weekly Training System"""
from db.mongodb import get_db
from engine.pipeline import get_learning_layer, get_trust_layer
from utils.feature_extractor import FeatureExtractor
from utils.logger import logger
from datetime import datetime

features = FeatureExtractor()

async def run_training() -> dict:
    db = get_db()
    layer = get_learning_layer()

    ratings = await db.ratings.find({}).to_list(5000)
    trained = 0
    for r in ratings:
        tool    = r.get("tool", "")
        preview = r.get("input_preview", "")
        rating  = r.get("rating", "")
        if not (tool and preview and rating):
            continue
        fv = features.extract(tool, preview)
        expected = 1.0 if rating == "like" else 0.0
        layer.update(tool, fv, expected, lr=0.005)
        trained += 1

    logger.info("training_complete", trained=trained, ts=datetime.utcnow().isoformat())
    return {"trained": trained, "timestamp": datetime.utcnow().isoformat()}
