# Services/StoryService.py
from FastAPIProject.Models.domain.story import Story
from FastAPIProject.Services.story_processor import StoryProcessor
from FastAPIProject.Models.domain.entity import Entity
from FastAPIProject.Models.domain.paragraph import Paragraph
from FastAPIProject.Repositories.story_repository import StoryRepository
from FastAPIProject.Models.api.story_models import StoryModel, EntityModel, ParagraphModel, StoryResponse, StoryCreate
from typing import List, Optional
import os


class StoryService:
    """שירות לניהול סיפורים - לוגיקה עסקית ואינטגרציה עם מסד נתונים"""

    def __init__(self):
        self.story_repository = StoryRepository()
        self.story_processor = StoryProcessor()

    def _entity_to_model(self, entity: Entity) -> EntityModel:
        """המרת Entity למודל של מסד הנתונים"""
        return EntityModel(
            name=entity.name,
            label=entity.label,
            nicknames=entity.nicknames if hasattr(entity, 'nicknames') else [],
            coref_position=entity.coref_position if hasattr(entity, 'coref_position') else [],
            description=entity.description if isinstance(entity.description, dict) else {},
        )

    def _paragraph_to_model(self, paragraph: Paragraph) -> ParagraphModel:
        """המרת Paragraph למודל של מסד הנתונים"""
        entities = [self._entity_to_model(entity) for entity in paragraph.entities if entity is not None]
        return ParagraphModel(
            index=paragraph.index,
            start=paragraph.start,
            end=paragraph.end,
            entities=entities,
            summary=paragraph.summary if hasattr(paragraph, 'summary') else None,
            place=paragraph.place if hasattr(paragraph, 'place') else None,
            time=paragraph.time if hasattr(paragraph, 'time') else None
        )

    def _story_to_model(self, story: Story, title: str, file_path: str, user_id: str) -> dict:
        """המרת Story למודל של מסד הנתונים"""
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

    async def create_story_from_file(self, story_create: StoryCreate, user_id: str) -> str:
        """יצירת סיפור מקובץ"""
        if not os.path.exists(story_create.file_path):
            raise FileNotFoundError(f"File not found: {story_create.file_path}")

        # בדיקה אם כבר קיים סיפור עם אותה כותרת עבור המשתמש
        existing_story = await self.story_repository.get_story_by_title_and_user(
            story_create.title, user_id
        )
        if existing_story:
            raise ValueError(f"Story with title '{story_create.title}' already exists for this user")

        # try:
            # יצירת אובייקט Story מהקובץ באמצעות StoryProcessor
        story = self.story_processor.create_story_from_file(story_create.file_path)

        # בדיקה שהסיפור לא ריק
        if story.is_empty():
            raise ValueError("The processed story is empty or invalid")

        # המרה למודל של מסד הנתונים
        story_data = self._story_to_model(story, story_create.title, story_create.file_path, user_id)

        # שמירה במסד הנתונים
        story_id = await self.story_repository.create_story(story_data, user_id)

        return story_id

        # except Exception as e:
        #     raise Exception(f"Failed to create story: {str(e)}")

    async def get_story(self, story_id: str, user_id: str) -> Optional[dict]:
        """קבלת סיפור לפי ID (רק אם שייך למשתמש)"""
        story = await self.story_repository.get_story_by_id(story_id)

        if story and story.get("user_id") == user_id:
            return story
        return None

    async def get_user_stories(self, user_id: str) -> List[StoryResponse]:
        """קבלת כל הסיפורים של משתמש"""
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

    async def update_story(self, story_id: str, user_id: str, update_data: dict) -> bool:
        """עדכון סיפור"""
        # וידוא שהסיפור שייך למשתמש
        story = await self.get_story(story_id, user_id)
        if not story:
            return False

        return await self.story_repository.update_story(story_id, update_data)

    async def delete_story(self, story_id: str, user_id: str) -> bool:
        """מחיקת סיפור"""
        # וידוא שהסיפור שייך למשתמש לפני המחיקה
        story = await self.get_story(story_id, user_id)
        if not story:
            return False

        return await self.story_repository.delete_story(story_id, user_id)

    async def reprocess_story(self, story_id: str, user_id: str) -> bool:
        """עיבוד מחדש של סיפור קיים"""
        story_data = await self.get_story(story_id, user_id)
        if not story_data:
            return False

        try:
            # עיבוד מחדש של הקובץ
            new_story = self.story_processor.create_story_from_file(story_data["file_path"])

            # המרה למודל מעודכן
            updated_data = self._story_to_model(
                new_story,
                story_data["title"],
                story_data["file_path"],
                user_id
            )

            # עדכון במסד הנתונים
            return await self.story_repository.update_story(story_id, updated_data)

        except Exception as e:
            print(f"Failed to reprocess story: {str(e)}")
            return False

    def get_story_statistics(self, story: Story) -> dict:
        """קבלת סטטיסטיקות של סיפור"""
        return {
            "total_characters": len(story.text),
            "total_words": len(story.text.split()) if story.text else 0,
            "chapters_count": story.get_chapter_count(),
            "paragraphs_count": story.get_paragraph_count(),
            "entities_count": story.get_entity_count(),
            "key_paragraphs_count": sum(len(chapter) for chapter in story.keyParagraphs)
        }