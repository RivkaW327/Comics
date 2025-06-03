# API/story_router.py
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordBearer
from typing import List, Any
import os
import tempfile
from jose import JWTError, jwt

from ..Services.story_service import StoryService
from ..Services.auth_service import AuthService
from ..Models.api.story_models import StoryCreate, StoryResponse
from ..config.config_loader import config

router = APIRouter(prefix="/stories", tags=["stories"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# קונפיגורציה של הטוקן (צריך להיות זהה לזה שב-auth)
SECRET_KEY = os.getenv("SECRET_KEY", config["jwt"]["secret_key"])
ALGORITHM = config["jwt"]["algorithm"]


async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
    """קבלת המשתמש הנוכחי מהטוקן"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # קבלת פרטי המשתמש מהמסד נתונים
    auth_service = AuthService()
    user = await auth_service.user_repository.get_user_by_username(username)
    if user is None:
        raise credentials_exception

    return str(user.id)


@router.post("/create", response_model=dict[str, Any])
async def create_story(
        story_create: StoryCreate,
        current_user_id: str = Depends(get_current_user_id)
):
    """יצירת סיפור חדש מקובץ קיים"""
    story_service = StoryService()

    try:
        story_id = await story_service.create_story_from_file(story_create, current_user_id)
        return {
            "message": "Story created successfully",
            "story_id": story_id,
            "title": story_create.title
        }
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create story: {str(e)}"
        )


@router.post("/upload-and-create", response_model=dict[str, Any])
async def upload_and_create_story(
        title: str,
        file: UploadFile = File(...),
        current_user_id: str = Depends(get_current_user_id)
):
    """העלאת קובץ ויצירת סיפור"""
    story_service = StoryService()

    # בדיקת סוג הקובץ
    if not file.filename.lower().endswith(('.pdf', '.txt', '.docx')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File type not supported. Please upload PDF, TXT, or DOCX files."
        )

    try:
        # יצירת קובץ זמני
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        # יצירת אובייקט StoryCreate
        story_create = StoryCreate(title=title, file_path=temp_file_path)

        # יצירת הסיפור
        story_id = await story_service.create_story_from_file(story_create, current_user_id)

        # מחיקת הקובץ הזמני
        os.unlink(temp_file_path)

        return {
            "message": "Story uploaded and created successfully",
            "story_id": story_id,
            "title": title,
            "original_filename": file.filename
        }

    except ValueError as e:
        # מחיקת הקובץ הזמני במקרה של שגיאה
        if 'temp_file_path' in locals():
            os.unlink(temp_file_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # מחיקת הקובץ הזמני במקרה של שגיאה
        if 'temp_file_path' in locals():
            os.unlink(temp_file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create story: {str(e)}"
        )


@router.get("/", response_model=List[StoryResponse])
async def get_user_stories(current_user_id: str = Depends(get_current_user_id)):
    """קבלת כל הסיפורים של המשתמש הנוכחי"""
    story_service = StoryService()

    try:
        stories = await story_service.get_user_stories(current_user_id)
        return stories
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stories: {str(e)}"
        )


@router.get("/{story_id}", response_model=dict[str, Any])
async def get_story(
        story_id: str,
        current_user_id: str = Depends(get_current_user_id)
):
    """קבלת סיפור לפי ID"""
    story_service = StoryService()

    try:
        story = await story_service.get_story(story_id, current_user_id)
        if not story:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Story not found or access denied"
            )

        return story
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get story: {str(e)}"
        )


@router.put("/{story_id}", response_model=dict[str, Any])
async def update_story(
        story_id: str,
        update_data: dict,
        current_user_id: str = Depends(get_current_user_id)
):
    """עדכון סיפור"""
    story_service = StoryService()

    try:
        success = await story_service.update_story(story_id, current_user_id, update_data)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Story not found or access denied"
            )

        return {"message": "Story updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update story: {str(e)}"
        )


@router.delete("/{story_id}", response_model=dict[str, Any])
async def delete_story(
        story_id: str,
        current_user_id: str = Depends(get_current_user_id)
):
    """מחיקת סיפור"""
    story_service = StoryService()

    try:
        success = await story_service.delete_story(story_id, current_user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Story not found or access denied"
            )

        return {"message": "Story deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete story: {str(e)}"
        )