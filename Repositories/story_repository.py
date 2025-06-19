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
        """create a new story and associate it with a user"""
        # save creation and update times
        story_data.update({
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        })

        # save in db
        result = await self.stories_collection.insert_one(story_data)
        story_id = str(result.inserted_id)

        # update user with the new story
        await self.users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$push": {"stories": story_id},
                "$set": {"updated_at": datetime.now()}
            }
        )

        return story_id

    async def get_story_by_id(self, story_id: str) -> Optional[Dict[str, Any]]:
        """get story by story ID"""
        try:
            story = await self.stories_collection.find_one({"_id": ObjectId(story_id)})
            return story
        except Exception:
            return None

    async def get_stories_by_user_id(self, user_id: str) -> List[Dict[str, Any]]:
        """get all stories for a specific user"""
        cursor = self.stories_collection.find({"user_id": user_id})
        stories = await cursor.to_list(length=None)
        return stories

    async def get_story_by_title_and_user(self, title: str, user_id: str) -> Optional[Dict[str, Any]]:
        """get story by title and user ID"""
        story = await self.stories_collection.find_one({
            "title": title,
            "user_id": user_id
        })
        return story

    # async def update_story(self, story_id: str, update_data: Dict[str, Any]) -> bool:
    #     """update a story"""
    #     update_data["updated_at"] = datetime.now()
    #
    #     result = await self.stories_collection.update_one(
    #         {"_id": ObjectId(story_id)},
    #         {"$set": update_data}
    #     )
    #
    #     return result.modified_count > 0

    # async def delete_story(self, story_id: str, user_id: str) -> bool:
    #     """delete story and update user stories list"""
    #     try:
    #         # delete the story from the stories collection
    #         delete_result = await self.stories_collection.delete_one({
    #             "_id": ObjectId(story_id),
    #             "user_id": user_id
    #         })
    #
    #         if delete_result.deleted_count > 0:
    #             # delete the story ID from the user's stories list
    #             await self.users_collection.update_one(
    #                 {"_id": ObjectId(user_id)},
    #                 {
    #                     "$pull": {"stories": story_id},
    #                     "$set": {"updated_at": datetime.now()}
    #                 }
    #             )
    #             return True
    #
    #         return False
    #     except Exception:
    #         return False
