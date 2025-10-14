from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime


class ReviewInfo(BaseModel):
    reviewers: List["ReviewerInfo"]


class ReviewerInfo(BaseModel):
    reviewer_id: str
    reviewer_email: Optional[str]
    review_scores: Optional[dict] = None
    review_total_score: Optional[float] = None
    review_decision: Optional[str] = None
    review_comments: Optional[str] = None
    total_coins_earned: Optional[float] = None


class PromptInfo(BaseModel):
    prompt_id: str
    sentence_id: str
    sentence_text: str
    media_url: Optional[str]
    category: str
    domain: str
    max_reuses: int
    current_reuses: int


class SubmissionInfo(BaseModel):
    submission_id: str
    user_id: str
    user_email: str
    type: str
    payload_text: Optional[str] = None
    file_url: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime


class TaskDetails(BaseModel):
    task_id: str
    assignment_id: Optional[str]
    assigned_at: Optional[datetime]
    status: Optional[str] = None
    prompt: PromptInfo
    submission: Optional[SubmissionInfo]
    review: Optional[ReviewInfo] = None
    is_reviewer: Optional[bool] = False
    user_email: Optional[str] = None


class ProjectTasksGeneralResponse(BaseModel):
    project_id: str
    project_name: str
    total_count: int
    limit: int
    offset: int
    returned_count: int
    tasks: List[TaskDetails]
