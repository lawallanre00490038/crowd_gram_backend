from email import message
from typing import List, Optional
from pandas.core.computation.ops import Op
from pydantic import BaseModel, EmailStr
from enum import Enum


class RoleEnum(str, Enum):
    agent = "agent"
    reviewer = "reviewer"
    admin = "admin"


# Request schema for registration
class UserRegisterRequest(BaseModel):
    name: str
    email: EmailStr
    role: RoleEnum = RoleEnum.agent
    password: Optional[str] = None
    telegram_id: Optional[str] = None
    languages: Optional[List[str]] = None
    dialects: Optional[List[str]] = None


# Response schema for user basic info
class UserResponse(BaseModel):
    message: Optional[str] = None
    id: str
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    telegram_id: Optional[str] = None
    role: RoleEnum
    languages: Optional[List[str]] = None
    dialects: Optional[List[str]] = None

    class Config:
        from_attributes = True


# Response schema for user status
class UserStatusResponse(BaseModel):
    role: RoleEnum
    languages: Optional[List[str]] = None
    dialects: Optional[List[str]] = None
    coins_earned: int

    total_tasks_assigned: Optional[int] = None
    completed_tasks: Optional[int] = None
    pending_tasks: Optional[int] = None
    sentences_read: Optional[int] = None

    tasks_assigned_to_review: Optional[int] = None
    completed_reviews: Optional[int] = None
