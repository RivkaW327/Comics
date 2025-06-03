from datetime import timedelta
from typing import Optional
from pydantic import EmailStr


from FastAPIProject.Repositories.user_repository import UserRepository
from FastAPIProject.Models.api.user import UserInDB, UserCreate, User, Token
from FastAPIProject.Services.utils.auth import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES


class AuthService:
    def __init__(self):
        self.user_repository = UserRepository()

    async def authenticate_user(self, email: EmailStr, password: str) -> Optional[UserInDB]:
        user = await self.user_repository.get_user_by_email(email)
        if not user:
            raise Exception(f"Email {email} not found")
        if not verify_password(password, user.hashed_password):
            raise Exception(f"Password {password} not correct")
        return user

    async def login(self, email: EmailStr, password: str) -> Optional[Token]:
        user = await self.authenticate_user(email, password)
        if not user:
            return None

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )

        return Token(access_token=access_token, token_type="bearer"), user

    async def register_user(self, user_create: UserCreate) -> Optional[User]:
        # בדיקה אם המשתמש כבר קיים
        existing_email = await self.user_repository.get_user_by_email(user_create.email)
        if existing_email:
            raise Exception(f"User {user_create.email} already exists")

        existing_user = await self.user_repository.get_user_by_email(user_create.username)
        if existing_user:
            raise Exception(f"UserName {user_create.username} already exists")

        # הצפנת הסיסמה
        hashed_password = get_password_hash(user_create.password)

        # יצירת המשתמש
        user_in_db = await self.user_repository.create_user(user_create, hashed_password)

        user = User(
            _id=str(user_in_db.id),
            username=user_in_db.username,
            email=user_in_db.email,
        )
        # יצירת טוקן גישה
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        token = Token(access_token=access_token, token_type="bearer")

        return user, token
