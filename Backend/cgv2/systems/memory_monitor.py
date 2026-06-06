"""Memory Monitor — يراقب RAM ويتصرف عند الضغط"""
import psutil
from utils.logger import logger

async def check_and_free(threshold_pct: float = 80.0):
    mem = psutil.virtual_memory()
    if mem.percent < threshold_pct:
        return {"action": "none", "memory_pct": mem.percent}

    logger.warning("high_memory", pct=mem.percent)

    # 1. تنظيف الكاش
    from systems.cache import result_cache
    cleaned = result_cache.cleanup()

    # 2. تشغيل النسيان الذكي
    from layers.layer12_forgetting import ForgettingLayer
    forgotten = await ForgettingLayer.run_cleanup()

    mem_after = psutil.virtual_memory().percent
    logger.info("memory_freed", before=mem.percent, after=mem_after,
                cache_cleaned=cleaned, forgotten=forgotten.get("forgotten",0))

    return {
        "action": "freed",
        "before_pct":    mem.percent,
        "after_pct":     mem_after,
        "cache_cleaned": cleaned,
        "forgotten":     forgotten.get("forgotten", 0)
    }
