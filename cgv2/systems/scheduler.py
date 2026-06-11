"""Scheduler — مهام تلقائية"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from utils.logger import logger

scheduler = AsyncIOScheduler()

async def _daily_cleanup():
    from layers.layer12_forgetting import ForgettingLayer
    result = await ForgettingLayer.run_cleanup()
    logger.info("daily_cleanup", forgotten=result.get("forgotten", 0))

async def _weekly_train():
    from systems.trainer import run_training
    result = await run_training()
    logger.info("weekly_training", result=result)

async def _hourly_cache_cleanup():
    from systems.cache import result_cache
    cleaned = result_cache.cleanup()
    logger.info("cache_cleanup", cleaned=cleaned)

async def _delete_old_uploads():
    import os, time
    upload_dir = "data/uploads"
    if not os.path.exists(upload_dir):
        return
    now = time.time()
    deleted = 0
    for f in os.listdir(upload_dir):
        fp = os.path.join(upload_dir, f)
        if os.path.isfile(fp) and (now - os.path.getmtime(fp)) > 86400:
            os.remove(fp)
            deleted += 1
    logger.info("uploads_cleanup", deleted=deleted)

def setup_scheduler():
    scheduler.add_job(_daily_cleanup,     "cron", hour=2,  minute=0)
    scheduler.add_job(_weekly_train,      "cron", day_of_week="sun", hour=3, minute=0)
    scheduler.add_job(_hourly_cache_cleanup, "interval", hours=1)
    scheduler.add_job(_delete_old_uploads,   "interval", hours=6)
    scheduler.start()
    logger.info("scheduler_started")
