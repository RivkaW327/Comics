from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional

from FastAPIProject.config.config_loader import config

class Database:
    client: Optional[AsyncIOMotorClient] = None
    db_name: str = config["database"]["name"]

    @classmethod
    async def connect_db(cls):
        # connect to mongoDB using the URI from the config
        mongo_url =  config["database"]["uri"]
        cls.client = AsyncIOMotorClient(mongo_url)

    @classmethod
    async def close_db(cls):
        if cls.client:
            cls.client.close()

    @classmethod
    def get_db(cls):
        return cls.client[cls.db_name]