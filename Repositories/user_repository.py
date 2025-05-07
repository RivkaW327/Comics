from bson import ObjectId
from datetime import datetime
from .database import Database
from models.user import UserInDB, UserCreate
from typing import Optional


class UserRepository:
    def __init__(self):
        self.db = Database.get_db()
        self.collection = self.db.users

    async def get_user_by_username(self, username: str) -> Optional[UserInDB]:
        user_data = await self.collection.find_one({"username": username})
        if user_data:
            return UserInDB(**user_data)
        return None

    async def get_user_by_email(self, email: str) -> Optional[UserInDB]:
        user_data = await self.collection.find_one({"email": email})
        if user_data:
            return UserInDB(**user_data)
        return None

    async def create_user(self, user: UserCreate, hashed_password: str) -> UserInDB:
        user_data = user.model_dump(exclude={"password"})
        user_data.update({
            "hashed_password": hashed_password,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        })

        result = await self.collection.insert_one(user_data)
        user_data["_id"] = result.inserted_id

        return UserInDB(**user_data)

    async def update_user(self, user_id: str, data: dict) -> Optional[UserInDB]:
        data["updated_at"] = datetime.now()

        await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": data}
        )

        user_data = await self.collection.find_one({"_id": ObjectId(user_id)})
        if user_data:
            return UserInDB(**user_data)
        return None