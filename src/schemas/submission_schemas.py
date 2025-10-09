from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from src.db.models import Status, TaskType

class SubmissionOut(BaseModel):
    project_name: Optional[str] = None
    project_id: Optional[str] = None
    submission_id: str
    user_id: str
    user_email: Optional[str]
    task_id: str
    assignment_id: Optional[str]
    type: TaskType
    status: Status
    file_url: Optional[str]
    payload_text: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


from typing import Optional, Dict
from pydantic import BaseModel
from datetime import datetime
from src.db.models import TaskType, Status

class PromptInfo(BaseModel):
    prompt_id: Optional[str] = None
    sentence_id: Optional[str] = None
    sentence_text: Optional[str] = None
    media_url: Optional[str] = None
    category: Optional[str] = None
    domain: Optional[str] = None

class SubmissionResponse(BaseModel):
    submission_id: str
    project_id: Optional[str] = None
    task_id: Optional[str] = None
    assignment_id: Optional[str] = None
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    type: Optional[TaskType] = None
    payload_text: Optional[str] = None
    file_url: Optional[str] = None
    status: Optional[Status] = None
    num_redo: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    prompt: Optional[PromptInfo] = None


    class Config:
        from_attributes = True
        fields = {"submission_id": "id"}


