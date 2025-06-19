from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Union
from datetime import datetime
from bson import ObjectId
from ..api.user import PyObjectId


class EntityModel(BaseModel):
    name: str
    label: str
    nicknames: List[str] = []
    coref_position: List[tuple[int, int]] = []
    description: Optional[Dict[str, str]] = None

    class Config:
        populate_by_name = True


class ParagraphModel(BaseModel):
    index: int
    start: int
    end: int
    entities: List[EntityModel] = []
    summary: Optional[str] = None
    place: Union[str, List[str], None] = None
    time: Union[str, List[str], None] = None

    class Config:
        populate_by_name = True


class StoryModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: str
    title: str
    text: str
    chapters: List[str] = []
    paragraphs: List[str] = []
    entities: List[EntityModel] = []
    key_paragraphs: List[List[ParagraphModel]] = []
    file_path: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    model_config = {
        "populate_by_name": True,
        "json_encoders": {ObjectId: str},
        "arbitrary_types_allowed": True
    }


class StoryCreate(BaseModel):
    title: str
    file_path: str

    class Config:
        populate_by_name = True


class StoryResponse(BaseModel):
    id: str
    title: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    chapters_count: int
    entities_count: int

    class Config:
        populate_by_name = True