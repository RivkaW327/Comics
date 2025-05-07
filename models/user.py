from pydantic import BaseModel, Field, EmailStr, GetJsonSchemaHandler
from typing import Optional, Annotated, Any
from datetime import datetime
from bson import ObjectId
from pydantic_core import core_schema


# מותאם עבור Pydantic V2
class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(
            cls, _source_type: Any, _handler: Any
    ) -> core_schema.CoreSchema:
        return core_schema.union_schema([
            core_schema.is_instance_schema(ObjectId),
            core_schema.chain_schema([
                core_schema.str_schema(),
                core_schema.no_info_plain_validator_function(cls.validate),
            ]),
        ])

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(
            cls, _schema: Any, handler: GetJsonSchemaHandler
    ) -> dict[str, Any]:
        return handler(str)


class UserBase(BaseModel):
    # full_name: Optional[str] = None
    username: str
    email: EmailStr

    class Config:
        populate_by_name = True


class UserCreate(UserBase):
    password: str


class UserInDB(UserBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    model_config = {
        "populate_by_name": True,
        "json_encoders": {ObjectId: str},
        "arbitrary_types_allowed": True
    }


class User(UserBase):
    id: str = Field(..., alias="_id")

    model_config = {
        "populate_by_name": True,
        "json_encoders": {ObjectId: str}
    }


class UserLogin(BaseModel):
    username: str
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None