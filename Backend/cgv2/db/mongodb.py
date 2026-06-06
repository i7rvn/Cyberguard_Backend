"""MongoDB Connection + Indexes"""
from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
from utils.logger import logger

client: AsyncIOMotorClient = None
db = None

async def connect():
    global client, db
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.DB_NAME]
    await _create_indexes()
    logger.info("mongodb_connected", db=settings.DB_NAME)

async def disconnect():
    global client
    if client:
        client.close()
        logger.info("mongodb_disconnected")

async def _create_indexes():
    await db.users.create_index("user_id", unique=True)
    await db.users.create_index("api_key")
    await db.knowledge.create_index("key", unique=True)
    await db.knowledge.create_index([("trust", -1)])
    await db.knowledge.create_index("created_at")
    await db.knowledge.create_index("type")
    await db.knowledge.create_index("deleted")
    await db.ratings.create_index([("key", 1), ("user_id", 1)])
    await db.scans.create_index("scan_id", unique=True)
    await db.scans.create_index("sha256")
    await db.scans.create_index("user_id")
    await db.scans.create_index("created_at")
    await db.cells.create_index("cell_id", unique=True)
    await db.hypotheses.create_index("status")
    await db.logs.create_index("timestamp")
    await db.logs.create_index("event")
    logger.info("mongodb_indexes_created")

def get_db():
    return db
