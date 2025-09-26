from typing import Optional, List, Dict, Any
from sqlalchemy import JSON
from sqlmodel import Field, SQLModel, Column, Relationship
import uuid
import sqlalchemy.dialects.postgresql as pg
from datetime import datetime
from enum import Enum


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
    approved = "approved"
    accepted = "accepted"
    reviewed = "reviewed"
    rejected = "rejected"
    under_review = "under_review"
    submitted = "submitted"




class Project(SQLModel, table=True):
    id: Optional[str] = Field(
        sa_column=Column(
            pg.VARCHAR,
            nullable=False,
            primary_key=True,
            default=lambda: str(uuid.uuid4())
        )
    )
    name: str
    description: Optional[str] = None
    per_user_quota: int = Field(default=180)
    reuse_count: Optional[int] = Field(default=None)
    agent_coin: float = Field(default=0.0)
    reviewer_coin: float = Field(default=0.0)
    is_public: bool = True

    # New fields for reviewer scoring
    # review_parameters: Optional[List[str]] = Field(sa_column=Column(pg.ARRAY(pg.VARCHAR))) 
    review_parameters: Optional[List[str]] = Field(default=[], sa_column=Column(pg.JSON))
    review_scale: Optional[int] = Field(default=5)  # max score per parameter
    review_threshold_percent: Optional[float] = Field(default=50.0)  # percent required to accept submission

    # relationships
    sentences: List["ProjectSentence"] = Relationship(back_populates="project")
    allocations: List["ProjectAllocation"] = Relationship(back_populates="project")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})


class ProjectReviewScore(SQLModel, table=True):
    id: Optional[str] = Field(
        sa_column=Column(
            pg.VARCHAR,
            nullable=False,
            primary_key=True,
            default=lambda: str(uuid.uuid4())
        )
    )
    submission_id: str = Field(foreign_key="audiosubmission.id")  # also can be TextSubmission or ImageSubmission
    reviewer_id: str = Field(foreign_key="user.id")
    scores: Optional[dict] = Field(sa_column=Column(pg.JSON))  # {"accuracy":4,"contextual":5,"alignment":3}
    total_score: float
    approved: bool
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProjectSentence(SQLModel, table=True):
    id: Optional[str] = Field(
        sa_column=Column(
            pg.VARCHAR,
            nullable=False,
            primary_key=True,
            default=lambda: str(uuid.uuid4())
        )
    )
    
    project_id: str = Field(foreign_key="project.id")
    sentence_id: str
    content: str
    max_reuses: Optional[int] = None
    current_reuses: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    project: Project = Relationship(back_populates="sentences")

    

class ProjectAllocation(SQLModel, table=True):
    id: Optional[str] = Field(
        sa_column=Column(
            pg.VARCHAR,
            nullable=False,
            primary_key=True,
            default=lambda: str(uuid.uuid4())
        )
    )
    project_id: str = Field(foreign_key="project.id")
    sentence_id: str = Field(foreign_key="projectsentence.id")
    user_id: Optional[str] = Field(foreign_key="user.id")
    user_email: Optional[str] = None
    assigned_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(default="assigned") # assigned, submitted, in_review, accepted, rejected, revoked
    submission_id: Optional[str] = Field(default=None, foreign_key="audiosubmission.id")


    project: Project = Relationship(back_populates="allocations")
    sentence: ProjectSentence = Relationship()
    user: "User" = Relationship(back_populates="allocations")


class User(SQLModel, table=True):
    id: Optional[str] = Field(
        sa_column=Column(
            pg.VARCHAR,
            nullable=False,
            primary_key=True,
            default=lambda: str(uuid.uuid4())
        )
    )
    name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    role: Role = Field(default=Role.agent)
    gender: Optional[Gender] = None
    age_group: Optional[str] = None
    edu_level: Optional[str] = None
    languages: Optional[str] = None
    telegram_id: Optional[str] = None

    # Relationships
    text_submissions: List["TextSubmission"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"foreign_keys": "[TextSubmission.user_id]"}
    )
    image_submissions: List["ImageSubmission"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"foreign_keys": "[ImageSubmission.user_id]"}
    )
    audio_submissions: List["AudioSubmission"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"foreign_keys": "[AudioSubmission.user_id]"}
    )

    # Reviewers
    reviewed_audios: List["AudioSubmission"] = Relationship(
        back_populates="reviewer",
        sa_relationship_kwargs={"foreign_keys": "[AudioSubmission.reviewer_id]"}
    )
    reviewed_texts: List["TextSubmission"] = Relationship(
        back_populates="reviewer",
        sa_relationship_kwargs={"foreign_keys": "[TextSubmission.reviewer_id]"}
    )
    reviewed_images: List["ImageSubmission"] = Relationship(
        back_populates="reviewer",
        sa_relationship_kwargs={"foreign_keys": "[ImageSubmission.reviewer_id]"}
    )

    coins_earned: List["CoinPayment"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"foreign_keys": "[CoinPayment.user_id]"}
    )
    audit_logs: List["AuditLog"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"foreign_keys": "[AuditLog.user_id]"}
    )
    allocations: List[ProjectAllocation] = Relationship(back_populates="user")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now, sa_column_kwargs={"onupdate": datetime.now})



class AudioSubmission(SQLModel, table=True):
    id: Optional[str] = Field(
        sa_column=Column(
            pg.VARCHAR,
            nullable=False,
            primary_key=True,
            default=lambda: str(uuid.uuid4())
        )
    )
    user_id: str = Field(foreign_key="user.id")
    # task_id: str = Field(foreign_key="task.id")
    task_id: str = Field(foreign_key="projectsentence.id")
    reviewer_id: Optional[str] = Field(default=None, foreign_key="user.id")

    s3_audio_path: Optional[str] = None
    duration: Optional[float] = None
    transcript: Optional[str] = None
    review_scores: Optional[str] = None
    status: Status = Field(default=Status.submitted)

    # Relationships
    user: "User" = Relationship(
        back_populates="audio_submissions",
        sa_relationship_kwargs={"foreign_keys": "[AudioSubmission.user_id]"}
    )
    reviewer: "User" = Relationship(
        back_populates="reviewed_audios",
        sa_relationship_kwargs={"foreign_keys": "[AudioSubmission.reviewer_id]"}
    )

    task: Optional["Task"] = Relationship(back_populates="audio_submissions")

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now, sa_column_kwargs={"onupdate": datetime.now})




class AuditLog(SQLModel, table=True):
    id: Optional[str] = Field(
        sa_column=Column(
            pg.VARCHAR,
            nullable=False,
            primary_key=True,
            default=lambda: str(uuid.uuid4())
        )
    )
    user_id: str = Field(foreign_key="user.id")
    action_type: str
    details: Optional[str] = None

    user: User = Relationship(back_populates="audit_logs")

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now, sa_column_kwargs={"onupdate": datetime.now})




class TextPrompt(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    content: str = Field(index=True, unique=True)
    domain: Optional[str] = None
    category: Optional[str] = None
    max_reuses: Optional[int] = Field(default=None)
    current_reuses: Optional[int] = Field(default=0)

    # Relationship
    tasks: List[Optional["Task"]] = Relationship(back_populates="text_prompt")


class Task(SQLModel, table=True):
    id: Optional[str] = Field(
        sa_column=Column(
            pg.VARCHAR,
            nullable=False,
            primary_key=True,
            default=lambda: str(uuid.uuid4())
        )
    )
    type: Optional[TaskType] = Field(default=TaskType.audio)
    content: Optional[str] = None
    domain: Optional[str] = None
    category: Optional[str] = None
    assigned_to: Optional[str] = Field(default=None, foreign_key="user.id")
    status: Status = Field(default=Status.pending)
    deadline: Optional[datetime] = None

    # Foreign key for TextPrompt (for audio tasks)
    text_prompt_id: Optional[int] = Field(default=None, foreign_key="textprompt.id")
    text_prompt: Optional[TextPrompt] = Relationship(back_populates="tasks")

    # Relationships
    allocations: List["TaskAllocation"] = Relationship(back_populates="task")
    audio_submissions: List["AudioSubmission"] = Relationship(back_populates="task")
    text_submissions: List["TextSubmission"] = Relationship(back_populates="task")
    image_submissions: List["ImageSubmission"] = Relationship(back_populates="task")
    coin_payments: List["CoinPayment"] = Relationship(back_populates="task")

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now, sa_column_kwargs={"onupdate": datetime.now})




class CoinPayment(SQLModel, table=True):
    id: Optional[str] = Field(
        sa_column=Column(
            pg.VARCHAR,
            nullable=False,
            primary_key=True,
            default=lambda: str(uuid.uuid4())
        )
    )
    user_id: str = Field(foreign_key="user.id")
    task_id: Optional[str] = Field(foreign_key="task.id")
    coins_earned: float
    approved: bool = Field(default=False)

    project_id: Optional[str] = Field(foreign_key="project.id")
    allocation_id: Optional[str] = Field(foreign_key="projectallocation.id")

    # Relationships

    user: User = Relationship(back_populates="coins_earned")
    task: Optional[Task] = Relationship(back_populates="coin_payments")

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now, sa_column_kwargs={"onupdate": datetime.now})



class TextSubmission(SQLModel, table=True):
    id: Optional[str] = Field(
        sa_column=Column(
            pg.VARCHAR,
            nullable=False,
            primary_key=True,
            default=lambda: str(uuid.uuid4())
        )
    )
    user_id: str = Field(foreign_key="user.id")
    # task_id: str = Field(foreign_key="task.id")
    task_id: str = Field(foreign_key="projectsentence.id")
    source_text: str
    translated_text: str
    status: Status
    reviewer_id: Optional[str] = Field(default=None, foreign_key="user.id")


    task: Optional["Task"] = Relationship(back_populates="text_submissions")

     # Explicitly say which FK belongs to which relationship
    user: "User" = Relationship(
        back_populates="text_submissions",
        sa_relationship_kwargs={"foreign_keys": "[TextSubmission.user_id]"}
    )
    reviewer: Optional["User"] = Relationship(
        back_populates="reviewed_texts",
        sa_relationship_kwargs={"foreign_keys": "[TextSubmission.reviewer_id]"}
    )
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(
        default_factory=datetime.now,
        sa_column_kwargs={"onupdate": datetime.now}
    )


class ImageSubmission(SQLModel, table=True):
    id: Optional[str] = Field(
        sa_column=Column(
            pg.VARCHAR,
            nullable=False,
            primary_key=True,
            default=lambda: str(uuid.uuid4())
        )
    )
    user_id: str = Field(foreign_key="user.id")
    # task_id: str = Field(foreign_key="task.id")
    task_id: str = Field(foreign_key="projectsentence.id")
    s3_image_path: str
    annotations: Optional[str] = None
    status: Status
    reviewer_id: Optional[str] = Field(default=None, foreign_key="user.id")

    # Relationships
    # Relationships
    user: "User" = Relationship(
        back_populates="image_submissions",
        sa_relationship_kwargs={"foreign_keys": "[ImageSubmission.user_id]"}
    )
    reviewer: Optional["User"] = Relationship(
        back_populates="reviewed_images",
        sa_relationship_kwargs={"foreign_keys": "[ImageSubmission.reviewer_id]"}
    )
    task: Optional["Task"] = Relationship(back_populates="image_submissions")

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now, sa_column_kwargs={"onupdate": datetime.now})


class TaskAllocation(SQLModel, table=True):
    task_id: str = Field(foreign_key="task.id", primary_key=True)
    user_id: str = Field(foreign_key="user.id", primary_key=True)
    assigned_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    status: Status = Field(default=Status.assigned)

    # Relationships
    task: Optional["Task"] = Relationship(back_populates="allocations")
    user: User = Relationship(back_populates="tasks_allocated")

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now, sa_column_kwargs={"onupdate": datetime.now})

