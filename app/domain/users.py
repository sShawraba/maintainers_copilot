from fastapi_users import schemas

class UserRead(schemas.BaseUser[int]):
    role: str

    class Config:
        from_attributes = True

class UserCreate(schemas.BaseUserCreate):
    pass