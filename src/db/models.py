from typing import Optional, List, Dict
from enum import Enum
from datetime import datetime
import uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import String
from sqlalchemy.orm import relationship as sa_relationship
from sqlmodel import SQLModel, Field, Relationship, Column
import sqlalchemy.dialects.postgresql as pg


# ----------------------------
# Helpers
# ----------------------------
def generate_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.utcnow()


# ----------------------------
# Enums
# ----------------------------
class Role(str, Enum):
    admin = "admin"
    agent = "agent"
    reviewer = "reviewer"
    super_reviewer = "super_reviewer"


class Gender(str, Enum):
    male = "male"
    female = "female"
    other = "other"


class TaskType(str, Enum):
    audio = "audio"
    text = "text"
    image = "image"
    video = "video"


class Status(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    assigned = "assigned"
    submitted = "submitted"
    under_review = "under_review"
    reviewed = "reviewed"
    accepted = "accepted"
    approved = "approved"
    rejected = "rejected"
    revoked = "revoked"


# ----------------------------
# Core models
# ----------------------------
class Project(SQLModel, table=True):
    """
    Project (aka Batch): top-level container.
    Stores defaults (payments, quotas, review config) and relationships.
    """
    id: Optional[str] = Field(
        sa_column=Column(pg.VARCHAR, primary_key=True, default=generate_uuid)
    )
    name: str
    description: Optional[str] = None

    # quotas & reuse defaults
    per_user_quota: int = Field(default=180)
    reuse_count: Optional[int] = Field(default=None)

    # default coin values (per-task)
    agent_coin: float = Field(default=0.0)
    reviewer_coin: float = Field(default=0.0)
    super_reviewer_coin: float = Field(default=0.0)

    # default fiat amounts (optional)
    agent_amount: float = Field(default=0.0)
    reviewer_amount: float = Field(default=0.0)
    super_reviewer_amount: float = Field(default=0.0)

    is_public: bool = Field(default=True)

    # reviewer scoring config
    review_parameters: Optional[List[str]] = Field(default=[], sa_column=Column(pg.JSON))
    review_scale: int = Field(default=5)
    review_threshold_percent: float = Field(default=50.0)

    # denormalized counters for quick dashboard (optional; update via job/trigger)
    total_prompts: int = Field(default=0)
    total_tasks: int = Field(default=0)
    total_submissions: int = Field(default=0)

    # relationships
    prompts: List["Prompt"] = Relationship(back_populates="project")
    tasks: List["Task"] = Relationship(back_populates="project")
    allocations: List["ProjectAllocation"] = Relationship(back_populates="project")

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow, sa_column_kwargs={"onupdate": utcnow})


class Prompt(SQLModel, table=True):
    """
    Prompt = a sentence/text snippet or reference to a media file that contributors will work on.
    Prompts belong to Projects and can spawn multiple Tasks (reused).
    """
    id: Optional[str] = Field(sa_column=Column(pg.VARCHAR, primary_key=True, default=generate_uuid))
    project_id: str = Field(foreign_key="project.id")
    text: Optional[str] = None            # the sentence / prompt text
    media_url: Optional[str] = None       # optional reference for media prompts
    domain: Optional[str] = None
    category: Optional[str] = None        # e.g., "read", "translate", "codemix"
    max_reuses: Optional[int] = Field(default=1)
    current_reuses: int = Field(default=0)

    # denormalized counters (helpful for quick metrics)
    total_allocated: int = Field(default=0)
    total_submitted: int = Field(default=0)
    total_accepted: int = Field(default=0)
    total_rejected: int = Field(default=0)

    # relationships
    project: Project = Relationship(back_populates="prompts")
    tasks: List["Task"] = Relationship(back_populates="prompt")

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow, sa_column_kwargs={"onupdate": utcnow})


class User(SQLModel, table=True):
    id: Optional[str] = Field(sa_column=Column(pg.VARCHAR, primary_key=True, default=generate_uuid))
    name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    role: Role = Field(default=Role.agent)
    gender: Optional[Gender] = None
    age_group: Optional[str] = None
    edu_level: Optional[str] = None
    
    languages: Optional[List[str]] = Field(default=[], sa_column=Column(JSONB))
    dialects: Optional[List[str]] = Field(default=[], sa_column=Column(JSONB))

    country: Optional[str] = None
    telegram_id: Optional[str] = None

    # relationships
    tasks_assigned: List["ProjectAllocation"] = Relationship(back_populates="user")
    reviewer_allocations: List["ReviewerAllocation"] = Relationship(back_populates="reviewer")
    submissions: List["Submission"] = Relationship(back_populates="user")
    reviews: List["Review"] = Relationship(back_populates="reviewer")
    coins_earned: List["CoinPayment"] = Relationship(back_populates="user")
    audit_logs: List["AuditLog"] = Relationship(back_populates="user")


    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow, sa_column_kwargs={"onupdate": utcnow})

    @property
    def pending_reviews(self):
        return [ra for ra in self.reviewer_allocations if ra.status == Status.pending]



class Task(SQLModel, table=True):
    """
    Task = an assignment generated from a Prompt and Project.
    Usually one Task corresponds to one Prompt being allocated to someone (but remains a separate entity).
    """
    id: Optional[str] = Field(sa_column=Column(pg.VARCHAR, primary_key=True, default=generate_uuid))
    project_id: str = Field(foreign_key="project.id")
    prompt_id: Optional[str] = Field(default=None, foreign_key="prompt.id")

    type: TaskType = Field(default=TaskType.audio)
    domain: Optional[str] = None
    category: Optional[str] = None

    # status describes the task lifecycle (assigned -> submitted -> reviewed -> accepted/rejected)
    status: Status = Field(default=Status.pending)
    deadline: Optional[datetime] = None

    # denormalized counters for quick metrics
    submission_count: int = Field(default=0)
    review_count: int = Field(default=0)
    accept_count: int = Field(default=0)
    reject_count: int = Field(default=0)

     # relationships
    project: Project = Relationship(back_populates="tasks")
    prompt: Optional[Prompt] = Relationship(back_populates="tasks")
    allocations: List["ProjectAllocation"] = Relationship(back_populates="task")
    submissions: List["Submission"] = Relationship(back_populates="task")
    coin_payments: List["CoinPayment"] = Relationship(back_populates="task")
    assignments: List["ProjectAllocation"] = Relationship(back_populates="task")

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow, sa_column_kwargs={"onupdate": utcnow})



class ProjectAllocation(SQLModel, table=True):
    """
    A single assignment of a Task (prompt) to a User.
    A ProjectAllocation can have one Submission.
    """
    id: Optional[str] = Field(sa_column=Column(pg.VARCHAR, primary_key=True, default=generate_uuid))
    project_id: str = Field(foreign_key="project.id")
    task_id: str = Field(foreign_key="task.id")
    user_id: Optional[str] = Field(default=None, foreign_key="user.id")
    user_email: Optional[str] = None

    status: Status = Field(default=Status.assigned)
    assigned_at: datetime = Field(default_factory=utcnow)
    submitted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # relationships
    project: Project = Relationship(back_populates="allocations")
    task: "Task" = Relationship(back_populates="allocations")
    user: Optional[User] = Relationship(back_populates="tasks_assigned")
    
    # This relationship links to the Submission that references this allocation.
    submission: Optional["Submission"] = Relationship(back_populates="assignment")

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow, sa_column_kwargs={"onupdate": utcnow})


class ReviewerAllocation(SQLModel, table=True):
    id: Optional[str] = Field(sa_column=Column(pg.VARCHAR, primary_key=True, default=generate_uuid))
    submission_id: str = Field(foreign_key="submission.id", nullable=False)
    reviewer_id: str = Field(foreign_key="user.id", nullable=False)
    status: Status = Field(default=Status.pending)
    assigned_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = None

    # relationships
    submission: "Submission" = Relationship(back_populates="review_allocations")
    reviewer: User = Relationship(back_populates="reviewer_allocations")
    # reviewer: User = Relationship(back_populates="reviews")
    



class Submission(SQLModel, table=True):
    """
    Unified Submission model. Each submission is linked to a single ProjectAllocation.
    """
    id: Optional[str] = Field(sa_column=Column(pg.VARCHAR, primary_key=True, default=generate_uuid))
    task_id: str = Field(foreign_key="task.id")
    # This foreign key establishes the "many-to-one" side of the relationship.
    assignment_id: Optional[str] = Field(default=None, foreign_key="projectallocation.id")
    user_id: str = Field(foreign_key="user.id")

    type: TaskType = Field(default=TaskType.audio)

    # generic fields
    file_url: Optional[str] = None
    duration: Optional[float] = None
    payload_text: Optional[str] = None

    # review metadata
    status: Status = Field(default=Status.submitted)
    meta: Optional[Dict] = Field(default=None, sa_column=Column(pg.JSON))

    # relationships
    task: Task = Relationship(back_populates="submissions")
    
    # This relationship links back to the ProjectAllocation.
    assignment: Optional[ProjectAllocation] = Relationship(back_populates="submission")
    review_allocations: list["ReviewerAllocation"] = Relationship(back_populates="submission")

    
    user: User = Relationship(back_populates="submissions")
    reviews: List["Review"] = Relationship(back_populates="submission")

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow, sa_column_kwargs={"onupdate": utcnow})
    





class Review(SQLModel, table=True):
    """
    Review / scoring for a submission.
    One submission can have multiple reviews (AI/human/super).
    """
    id: Optional[str] = Field(sa_column=Column(pg.VARCHAR, primary_key=True, default=generate_uuid))
    submission_id: str = Field(foreign_key="submission.id")
    reviewer_id: str = Field(foreign_key="user.id")

    # review_level could be 'AI' / 'human' / 'super_reviewer'
    review_level: str = Field(default="human")
    scores: Optional[Dict] = Field(default=None, sa_column=Column(pg.JSON))  # param -> score
    total_score: Optional[float] = None
    decision: Optional[Status] = None  # accepted / rejected / redo
    comments: Optional[str] = None
    approved: Optional[bool] = None

    submission: Submission = Relationship(back_populates="reviews")
    reviewer: User = Relationship(back_populates="reviews")

    created_at: datetime = Field(default_factory=utcnow)


class CoinPayment(SQLModel, table=True):
    id: Optional[str] = Field(sa_column=Column(pg.VARCHAR, primary_key=True, default=generate_uuid))
    user_id: str = Field(foreign_key="user.id")
    task_id: Optional[str] = Field(foreign_key="task.id")
    assignment_id: Optional[str] = Field(foreign_key="projectallocation.id")
    project_id: Optional[str] = Field(foreign_key="project.id")

    coins_earned: float
    approved: bool = Field(default=False)

    user: User = Relationship(back_populates="coins_earned")
    task: Optional[Task] = Relationship(back_populates="coin_payments")

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow, sa_column_kwargs={"onupdate": utcnow})


class AuditLog(SQLModel, table=True):
    id: Optional[str] = Field(sa_column=Column(pg.VARCHAR, primary_key=True, default=generate_uuid))
    user_id: str = Field(foreign_key="user.id")
    action_type: str
    details: Optional[str] = None

    user: User = Relationship(back_populates="audit_logs")

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow, sa_column_kwargs={"onupdate": utcnow})

