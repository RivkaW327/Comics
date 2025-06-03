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


# @router.post("/login", response_model=Token)
# async def login(form_data: OAuth2PasswordRequestForm = Depends()):
#     auth_service = AuthService()
#     try:
#         token = await auth_service.login(form_data.email, form_data.password)
#     except(Exception) as e:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Incorrect username or password",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#
#     return token


# גרסה נוספת של login שמקבלת JSON במקום form data
@router.post("/login/json", response_model=dict[str, Any])
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

# router = APIRouter()

@router.get("/")
async def root():
    return {"message": "Hello World"}

@router.get("/hello/{name}")
async def say_hello(name: str):
    return HelloService.say_hello(name)


@router.get("/story/")
async def say_story():
    # path = "C:\\Users\\user\\Documents\\year2\\project\\data\\the_gift_of_the_magi.pdf"
    path = "C:/Users/user/Documents/year2/project/data/the_gift_of_the_magi.pdf"

    story_service = StoryService()

    story_data = await story_service.create_story_from_file(StoryCreate(file_path=path, title="the gift of the magi"), "681a40cc098976d95670ea18")
    try:
        print(story_data)
    except Exception as e:
        print(f"Error printing story data: {str(e)}")
    return {"message": "Story processed successfully", "story": story_data}
