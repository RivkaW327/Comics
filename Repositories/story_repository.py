# Repository/story_repository.py
from bson import ObjectId
from datetime import datetime
from .database import Database
from typing import List, Optional, Dict, Any


class StoryRepository:
    def __init__(self):
        self.db = Database.get_db()
        self.stories_collection = self.db.stories
        self.users_collection = self.db.users

    async def create_story(self, story_data: Dict[str, Any], user_id: str) -> str:
        """יצירת סיפור חדש ועדכון המשתמש"""
        # הוספת תאריכי יצירה ועדכון
        story_data.update({
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        })

        # שמירת הסיפור במסד הנתונים
        result = await self.stories_collection.insert_one(story_data)
        story_id = str(result.inserted_id)

        # עדכון המשתמש עם ה-ID של הסיפור החדש
        await self.users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$push": {"stories": story_id},
                "$set": {"updated_at": datetime.now()}
            }
        )

        return story_id

    async def get_story_by_id(self, story_id: str) -> Optional[Dict[str, Any]]:
        """קבלת סיפור לפי ID"""
        try:
            story = await self.stories_collection.find_one({"_id": ObjectId(story_id)})
            return story
        except Exception:
            return None

    async def get_stories_by_user_id(self, user_id: str) -> List[Dict[str, Any]]:
        """קבלת כל הסיפורים של משתמש"""
        cursor = self.stories_collection.find({"user_id": user_id})
        stories = await cursor.to_list(length=None)
        return stories

    async def update_story(self, story_id: str, update_data: Dict[str, Any]) -> bool:
        """עדכון סיפור"""
        update_data["updated_at"] = datetime.now()

        result = await self.stories_collection.update_one(
            {"_id": ObjectId(story_id)},
            {"$set": update_data}
        )

        return result.modified_count > 0

    async def delete_story(self, story_id: str, user_id: str) -> bool:
        """מחיקת סיפור ועדכון המשתמש"""
        try:
            # מחיקת הסיפור
            delete_result = await self.stories_collection.delete_one({
                "_id": ObjectId(story_id),
                "user_id": user_id
            })

            if delete_result.deleted_count > 0:
                # הסרת ה-ID של הסיפור מרשימת הסיפורים של המשתמש
                await self.users_collection.update_one(
                    {"_id": ObjectId(user_id)},
                    {
                        "$pull": {"stories": story_id},
                        "$set": {"updated_at": datetime.now()}
                    }
                )
                return True

            return False
        except Exception:
            return False

    async def get_story_by_title_and_user(self, title: str, user_id: str) -> Optional[Dict[str, Any]]:
        """קבלת סיפור לפי כותרת ומשתמש"""
        story = await self.stories_collection.find_one({
            "title": title,
            "user_id": user_id
        })
        return story