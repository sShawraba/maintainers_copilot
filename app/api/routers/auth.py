from fastapi import APIRouter
from fastapi_users import FastAPIUsers
from app.api.auth_backend import auth_backend
from app.db.user_manager import get_user_manager
from app.domain.users import UserRead, UserCreate
from app.db.models import User

fastapi_users = FastAPIUsers[User, int](
    get_user_manager,
    [auth_backend],
)

router = APIRouter()
router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth",
    tags=["auth"],
)

current_active_user = fastapi_users.current_user(active=True)