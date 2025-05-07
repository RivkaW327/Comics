from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
# import os

from FastAPIProject.config.config_loader import config

class Database:
    client: Optional[AsyncIOMotorClient] = None
    db_name: str = "app_db"

    @classmethod
    async def connect_db(cls):
        # קישור למונגו - ניתן להגדיר משתנה סביבה או להשתמש בערך ברירת מחדל
        mongo_url =  config["database"]["uri"]#os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        cls.client = AsyncIOMotorClient(mongo_url)

    @classmethod
    async def close_db(cls):
        if cls.client:
            cls.client.close()

    @classmethod
    def get_db(cls):
        return cls.client[cls.db_name]