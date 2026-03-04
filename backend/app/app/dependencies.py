from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

# MongoDB client
mongodb_client: AsyncIOMotorClient = None

async def get_database():
    return mongodb_client[settings.mongodb_db_name]

async def connect_to_mongo():
    global mongodb_client
    mongodb_client = AsyncIOMotorClient(settings.mongodb_url)

async def close_mongo_connection():
    global mongodb_client
    if mongodb_client:
        mongodb_client.close()

