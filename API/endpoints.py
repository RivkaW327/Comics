from typing import Any

from FastAPIProject.Models.domain.story import Story
# from FastAPIProject.Services.story_processor import StoryProcessor
from fastapi import APIRouter, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from FastAPIProject.Services.story_service import StoryService

from FastAPIProject.Models.api.story_models import StoryCreate
from FastAPIProject.Services.auth_service import AuthService
from FastAPIProject.Models.api.user import UserCreate, User, Token, UserLogin

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


@router.post("/register", response_model=dict[str, Any])
async def register(user_create: UserCreate):
    auth_service = AuthService()
    try:
        user, token = await auth_service.register_user(user_create)
    except(Exception) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.args[0]
        )

    return {"name": user.username, "email": user.email, "token": token}



@router.post("/login", response_model=dict[str, Any])
async def login_json(user_login: UserLogin):
    auth_service = AuthService()
    try:
        token, user = await auth_service.login(user_login.email, user_login.password)
    except(Exception) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.args[0]
        )

    return {"name": user.username, "email": user.email, "token": token} #{"token": token, "user": user}
