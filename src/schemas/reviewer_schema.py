from typing import Optional
from datetime import datetime
from pydantic import BaseModel


# ----------------------------
# Response Schemas
# ----------------------------
class PromptResponse(BaseModel):
    id: str
    text: Optional[str] = None

class FilterReviewResponse(BaseModel):
    reviewer_allocation_id: str
    submission_id: str
    sentence_id: Optional[str] = None
    prompt: Optional[str] = None
    file_url: Optional[str] = None
    payload_text: Optional[str] = None
    contributor_id: str
    status: str
    assigned_at: datetime

class ReviewerHistoryResponse(BaseModel):
    submission_id: str
    sentence_id: Optional[str] = None
    prompt: Optional[str] = None
    reviewer_id: str
    status: str
    reviewed_at: Optional[datetime] = None
