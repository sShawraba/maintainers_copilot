from typing import Optional
from fastapi import Depends, Request
from fastapi_users import BaseUserManager, IntegerIDMixin
from app.db.models import User
from app.db.user_db import get_user_db
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase

# In production, load from Vault
SECRET = "your-temporary-secret-change-this"

class UserManager(IntegerIDMixin, BaseUserManager[User, int]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        print(f"User {user.id} registered")

async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)