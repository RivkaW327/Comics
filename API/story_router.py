import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.security import OAuth2PasswordBearer
from typing import List, Any
import os
from jose import JWTError, jwt

from ..Services.story_service import StoryService
from ..Services.auth_service import AuthService
from ..Models.api.story_models import StoryCreate, StoryResponse
from ..config.config_loader import config

import traceback

router = APIRouter(prefix="/stories", tags=["stories"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

SECRET_KEY = os.getenv("SECRET_KEY", config["jwt"]["secret_key"])
ALGORITHM = config["jwt"]["algorithm"]

UPLOAD_DIR = Path(config["uploads"]["directory"])
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
    """get user by token"""
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

    # get user details from db
    auth_service = AuthService()
    user = await auth_service.user_repository.get_user_by_username(username)
    if user is None:
        raise credentials_exception

    return str(user.id)


def validate_pdf_file(file: UploadFile) -> None:
    """check if the file is a valid PDF file"""
    if file.content_type != 'application/pdf':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported. Please upload a PDF file."
        )

    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must have .pdf extension"
        )



@router.post("/upload-and-create", response_model=dict[str, Any])
async def upload_and_create_story(
        file: UploadFile = File(...),
        title: str = Form(None),
        current_user_id: str = Depends(get_current_user_id)
):
    """upload file and create a new operation"""
    story_service = StoryService()

    # check if the file is only PDF
    validate_pdf_file(file)

    # save title if provided, otherwise use filename or default title
    if not title or not title.strip():
        if file.filename:
            title = file.filename.replace('.pdf', '').replace('.PDF', '')
        else:
            title = "Untitled Story"

    title = title.strip()

    try:
        content = await file.read()

        # checking if the content start with PDF signature
        if not content.startswith(b'%PDF'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid PDF file format"
            )

        # create a unique filename
        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = UPLOAD_DIR / unique_filename

        # save the file
        with open(file_path, "wb") as f:
            f.write(content)

        story_create = StoryCreate(title=title, file_path=str(file_path))
        story_data = await story_service.create_story_from_file(story_create, current_user_id)

        return {
            "message": "PDF story uploaded and created successfully",
            "story": story_data,
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        traceback.print_exc()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create story: {str(e)}"
        )


@router.get("/", response_model=List[StoryResponse])
async def get_user_stories(current_user_id: str = Depends(get_current_user_id)):
    """get oll stories for the current user"""
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
    """get story by ID"""
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


# @router.put("/{story_id}", response_model=dict[str, Any])
# async def update_story(
#         story_id: str,
#         update_data: dict,
#         current_user_id: str = Depends(get_current_user_id)
# ):
#     """update story by ID"""
#     story_service = StoryService()
#
#     try:
#         success = await story_service.update_story(story_id, current_user_id, update_data)
#         if not success:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Story not found or access denied"
#             )
#
#         return {"message": "Story updated successfully"}
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to update story: {str(e)}"
#         )


# @router.delete("/{story_id}", response_model=dict[str, Any])
# async def delete_story(
#         story_id: str,
#         current_user_id: str = Depends(get_current_user_id)
# ):
#     """delete story by ID"""
#     story_service = StoryService()
#
#     try:
#         success = await story_service.delete_story(story_id, current_user_id)
#         if not success:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="Story not found or access denied"
#             )
#
#         return {"message": "Story deleted successfully"}
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to delete story: {str(e)}"
#         )