from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional
from typing import List, Optional
from pydantic import BaseModel, Field, conint, confloat
from typing import Dict

from src.db.models import TaskType



class ProjectCreate(BaseModel):
    id: Optional[str] = Field(None, description="Optional UUID for the project. Auto-generated if not provided.")
    name: str = Field(..., description="Unique name of the project.")
    description: Optional[str] = Field(None, description="Brief description of the project.")
    
    agent_quota: Optional[int] = Field(180, ge=0, description="Maximum tasks a single agent can complete.")
    reuse_quota: Optional[int] = Field(0, ge=0, description="Number of times tasks/prompts can be reused.")
    
    agent_coin: Optional[int] = Field(0, ge=0, description="Coins awarded to agents per completed task.")
    reviewer_coin: Optional[int] = Field(0, ge=0, description="Coins awarded to reviewers per reviewed submission.")
    super_reviewer_coin: Optional[int] = Field(0, ge=0, description="Coins awarded to super reviewers per review.")
    
    agent_amount: Optional[float] = Field(0.0, ge=0.0, description="Monetary reward for agents.")
    reviewer_amount: Optional[float] = Field(0.0, ge=0.0, description="Monetary reward for reviewers.")
    super_reviewer_amount: Optional[float] = Field(0.0, ge=0.0, description="Monetary reward for super reviewers.")
    
    is_public: Optional[bool] = Field(True, description="Whether the project is visible to all agents.")
    
    review_parameters: Optional[List[str]] = Field(default_factory=list, description="List of parameters to score submissions (e.g., ['accuracy', 'clarity']).")
    review_scale: Optional[int] = Field(5, ge=1, description="Maximum score for each review parameter.")
    review_threshold_percent: conint(ge=0, le=100) = Field(50, description="Minimum percent of total score required for approval.")
    
    total_prompts: Optional[int] = Field(0, ge=0, description="Total number of prompts in the project.")
    total_tasks: Optional[int] = Field(0, ge=0, description="Total number of tasks allocated in the project.")
    total_submissions: Optional[int] = Field(0, ge=0, description="Total number of submissions received for the project.")
    
    class Config:
        from_attributes = True  # Enables compatibility with SQLAlchemy models


class ReviewScores(BaseModel):
    comments: Optional[str] = None

    class Config:
        extra='allow' 
        

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None

    is_auto_review: Optional[bool] = False

    agent_coin: Optional[float] = None
    reviewer_coin: Optional[float] = None
    super_reviewer_coin: Optional[float] = None

    agent_amount: Optional[float] = None
    reviewer_amount: Optional[float] = None
    super_reviewer_amount: Optional[float] = None

    agent_instructions: Optional[str] = None
    reviewer_instructions: Optional[str] = None
    super_reviewer_instructions: Optional[str] = None

    agent_quota: Optional[int] = None
    reviewer_quota: Optional[int] = None
    reuse_count: Optional[int] = None

    review_parameters: Optional[List[str]] = None
    review_scale: Optional[int] = None
    review_threshold_percent: Optional[float] = None

    total_prompts: Optional[int] = None
    total_tasks: Optional[int] = None
    total_submissions: Optional[int] = None



class GetProjectInfo(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None

class AllocationOut(BaseModel):
    assignment_id: str   # <-- alias for allocation.id
    project_id: str
    task_id: Optional[str] = None
    user_id: str
    user_email: str
    status: str
    assigned_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True

class AllocationResponse(BaseModel):
    allocated_count: int
    allocations: List[str]

class TaskWithUser(BaseModel):
    task_id: str
    assignment_id: str
    prompt_id: str
    sentence_id: Optional[str]
    sentence_text: Optional[str]
    user_id: Optional[str]
    user_email: Optional[str]
    assigned_at: Optional[datetime] = None
    status: str

class ProjectTasksResponse(BaseModel):
    project_id: str
    project_name: str
    tasks: List[TaskWithUser]


class PromptInfo(BaseModel):
    prompt_id: Optional[str]
    sentence_id: Optional[str]  # same as prompt_id
    sentence_text: Optional[str]
    media_url: Optional[str]
    category: Optional[str]
    domain: Optional[str]
    max_reuses: Optional[int]
    current_reuses: Optional[int]

class SubmissionInfo(BaseModel):
    submission_id: str
    user_id: Optional[str]
    user_email: Optional[str]
    type: Optional[TaskType]
    payload_text: Optional[str]
    file_url: Optional[str]
    status: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

class ReviewerInfo(BaseModel):
    reviewer_id: str
    reviewer_email: Optional[str]
    review_scores: Optional[Dict] = None
    review_total_score: Optional[float] = None
    review_decision: Optional[str] = None
    review_comments: Optional[str] = None
    total_coins_earned: Optional[float] = 0

class ReviewInfo(BaseModel):
    reviewers: List[ReviewerInfo] = []

class TaskWithDetails(BaseModel):
    task_id: str
    assignment_id: Optional[str]
    assigned_at: Optional[datetime] = None
    status: Optional[str] = None
    prompt: Optional[PromptInfo] = None
    submission: Optional[SubmissionInfo] = None
    review: Optional[ReviewInfo] = None
    user_email: Optional[str] = None


class ProjectTasksResponseRich(BaseModel):
    project_id: str
    project_name: str
    tasks: list[TaskWithDetails]




class ReviewDetail(BaseModel):
    review_scores: Optional[Dict[str, int]]
    review_total_score: Optional[int]
    review_decision: Optional[str]
    review_comments: Optional[str]
    total_coins_earned: int

class ReviewerTaskResponse(BaseModel):
    task_id: str
    assignment_id: str
    assigned_at: str
    status: str
    prompt: dict 
    submission: dict
    review: Optional[ReviewDetail]






class TaskWithDetailsReview(BaseModel):
    task_id: str
    assignment_id: Optional[str]
    assigned_at: Optional[datetime] = None
    status: Optional[str] = None
    prompt: Optional[PromptInfo] = None
    submission: Optional[SubmissionInfo] = None

class ReviewerWithTasks(BaseModel):
    reviewer_id: str
    reviewer_email: str
    tasks: List[TaskWithDetailsReview]

class ProjectReviewerTasksResponse(BaseModel):
    project_id: str
    project_name: str
    reviewers: List[ReviewerWithTasks]





class AddProjectReviewersRequest(BaseModel):
    emails: List[str]






# class ProjectTasksGeneralResponse(BaseModel):
#     project_id: str
#     project_name: str
#     total_count: int
#     limit: int
#     offset: int
#     returned_count: int
#     tasks: List[TaskDetails]


# class ReviewerTasksResponse(BaseModel):
#     reviewer_id: str
#     reviewer_email: str
#     tasks: List[TaskDetails]


# class ProjectReviewerTasksResponse(BaseModel):
#     project_id: str
#     project_name: str
#     total_count: int
#     limit: int
#     offset: int
#     returned_count: int
#     reviewers: List[ReviewerTasksResponse]

