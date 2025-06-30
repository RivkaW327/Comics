from FastAPIProject.Models.domain.story import Story
from FastAPIProject.Services.story_processor import StoryProcessor
from FastAPIProject.Models.domain.entity import Entity
from FastAPIProject.Models.domain.paragraph import Paragraph
from FastAPIProject.Repositories.story_repository import StoryRepository
from FastAPIProject.Models.api.story_models import StoryModel, EntityModel, ParagraphModel, StoryResponse, StoryCreate
from typing import List, Optional, Dict, Any
from bson import ObjectId
import os


class StoryService:
    """Service for managing stories, including creation and retrieval"""

    def __init__(self):
        self.story_repository = StoryRepository()
        self.story_processor = StoryProcessor()

    def _convert_objectid_to_string(self, data: Any) -> Any:
        """convert ObjectId to string recursively"""
        if isinstance(data, ObjectId):
            return str(data)
        elif isinstance(data, dict):
            return {key: self._convert_objectid_to_string(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._convert_objectid_to_string(item) for item in data]
        else:
            return data

    def _entity_to_model(self, entity: Entity) -> EntityModel:
        """convert Entity to database model"""
        return EntityModel(
            name=entity.name,
            label=entity.label,
            nicknames=entity.nicknames if hasattr(entity, 'nicknames') else [],
            coref_position=entity.coref_position if hasattr(entity, 'coref_position') else [],
            description=entity.description if isinstance(entity.description, dict) else {},
        )

    def _paragraph_to_model(self, paragraph: Paragraph) -> ParagraphModel:
        """covert Paragraph to database model"""
        return ParagraphModel(
            index=paragraph.index,
            start=paragraph.start,
            end=paragraph.end,
            entities=paragraph.entities,
            summary=paragraph.summary if hasattr(paragraph, 'summary') else None,
            place=paragraph.place if hasattr(paragraph, 'place') else None,
            time=paragraph.time if hasattr(paragraph, 'time') else None
        )

    def _story_to_model(self, story: Story, title: str, file_path: str, user_id: str) -> dict:
        """convert Story to database model"""
        entities = []
        if story.entities:
            entities = [self._entity_to_model(entity) for entity in story.entities]

        key_paragraphs = []
        if story.keyParagraphs:
            for chapter_paragraphs in story.keyParagraphs:
                chapter_models = [self._paragraph_to_model(paragraph) for paragraph in chapter_paragraphs]
                key_paragraphs.append(chapter_models)

        return {
            "user_id": user_id,
            "title": title,
            "text": story.text,
            "chapters": story.chapters,
            "paragraphs": story.paragraphs,
            "entities": [entity.dict() for entity in entities],
            "key_paragraphs": [[paragraph.dict() for paragraph in chapter] for chapter in key_paragraphs],
            "file_path": file_path
        }

    async def create_story_from_file(self, story_create: StoryCreate, user_id: str) -> Dict[str, Any]:
        """create a new story from a file"""
        if not os.path.exists(story_create.file_path):
            raise FileNotFoundError(f"File not found: {story_create.file_path}")

        # if the story already exists for the user, raise an error
        existing_story = await self.story_repository.get_story_by_title_and_user(
            story_create.title, user_id
        )
        if existing_story:
            raise ValueError(f"Story with title '{story_create.title}' already exists for this user")

        try:
            # create a Story object from the file using StoryProcessor
            story = self.story_processor.create_story_from_file(story_create.file_path)

            if story.is_empty():
                raise ValueError("The processed story is empty or invalid")
            story_data = self._story_to_model(story, story_create.title, story_create.file_path, user_id)

            # save in db
            story_id = await self.story_repository.create_story(story_data, user_id)

            # get full story data after creation
            full_story = await self.story_repository.get_story_by_id(story_id)

            # convert ObjectId to string
            return self._convert_objectid_to_string(full_story)

        except Exception as e:
            raise Exception(f"Failed to create story: {str(e)}")

    async def get_story(self, story_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """get story by ID for a specific user"""
        story = await self.story_repository.get_story_by_id(story_id)

        if story and story.get("user_id") == user_id:
            return self._convert_objectid_to_string(story)
        return None

    async def get_user_stories(self, user_id: str) -> List[StoryResponse]:
        """get all stories for a specific user"""
        stories = await self.story_repository.get_stories_by_user_id(user_id)

        story_responses = []
        for story in stories:
            story_response = StoryResponse(
                id=str(story["_id"]),
                title=story["title"],
                user_id=story["user_id"],
                created_at=story["created_at"],
                updated_at=story["updated_at"],
                chapters_count=len(story.get("chapters", [])),
                entities_count=len(story.get("entities", []))
            )
            story_responses.append(story_response)

        return story_responses

    # async def update_story(self, story_id: str, user_id: str, update_data: dict) -> bool:
    #     """update an existing story"""
    #
    #     # check if the story exists and belongs to the user
    #     story = await self.get_story(story_id, user_id)
    #     if not story:
    #         return False
    #
    #     return await self.story_repository.update_story(story_id, update_data)
    #
    # async def delete_story(self, story_id: str, user_id: str) -> bool:
    #     """delete a story by ID for a specific user"""
    #
    #     # before deleting, check if the story exists and belongs to the user
    #     story = await self.get_story(story_id, user_id)
    #     if not story:
    #         return False
    #
    #     return await self.story_repository.delete_story(story_id, user_id)

    def get_story_statistics(self, story: Story) -> dict:
        """get statistics for a given story"""
        return {
            "total_characters": len(story.text),
            "total_words": len(story.text.split()) if story.text else 0,
            "chapters_count": story.get_chapter_count(),
            "paragraphs_count": story.get_paragraph_count(),
            "entities_count": story.get_entity_count(),
            "key_paragraphs_count": sum(len(chapter) for chapter in story.keyParagraphs)
        }