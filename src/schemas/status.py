from typing import Optional
from uuid import UUID
from pydantic import BaseModel
from typing import Optional, List
from src.db.models import Status  # import your Enum

class ProjectResponse(BaseModel):
    id: str
    name: str

    class Config:
        from_attributes = True


class ProjectAllocationResponse(BaseModel):
    id: str
    user_id: str
    user_email: str
    status: Status
    project: Optional[ProjectResponse] = None

    class Config:
        from_attributes = True




# Analytics Schemas

class ProjectContributorStats(BaseModel):
    project_id: str
    project_name: str
    total: int
    number_assigned: int
    total_submissions: int
    approved: int
    rejected: int
    pending: int
    total_coins_earned: int
    total_amount_earned: float

class ContributorStats(BaseModel):
    user_email: str
    approved: int
    pending: int
    rejected: int
    per_project: List[ProjectContributorStats]



class ProjectReviewerStats(BaseModel):
    project_id: str
    project_name: str
    total_reviewed: int
    approved: int
    rejected: int
    pending: int
    number_assigned: int
    total_coins_earned: int
    total_amount_earned: float

class ReviewerStats(BaseModel):
    reviewer_email: str
    total_reviewed: int
    approved_reviews: int
    rejected_reviews: int
    pending_reviews: int
    per_project: List[ProjectReviewerStats]


class PlatformStats(BaseModel):
    total_users: int
    total_projects: int
    total_allocations: int
    total_submissions: int
    approved_submissions: int
    rejected_submissions: int
    pending_review_submissions: int
    total_coins_paid: int


class DailyStats(BaseModel):
    date: str  # ISO date string
    audio_submissions: int
    text_submissions: int
    image_submissions: int
    video_submissions: int
    total_submissions: int


class DailyStatsResponse(BaseModel):
    data: List[DailyStats]

