from typing import Optional
from sqlmodel import SQLModel
from src.db.models import Role

class Token(SQLModel):
    access_token: str
    token_type: str

class UserCreate(SQLModel):
    name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    role: Role = Role.agent
    gender: Optional[str] = None
    age_group: Optional[str] = None
    edu_level: Optional[str] = None
    languages: Optional[str] = None
    telegram_id: Optional[str] = None


class UserLogin(SQLModel):
    email: Optional[str] = None
    password: Optional[str] = None
    telegram_id: Optional[str] = None


    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "mary@example.com",
                "password": "pass123",
            }
        }
    }