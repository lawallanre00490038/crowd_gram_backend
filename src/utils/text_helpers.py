from typing import Optional
from src.db.models import Submission, Prompt

def get_effective_payload_text(submission: Optional[Submission], prompt: Optional[Prompt]) -> Optional[str]:
    """
    Returns the effective payload text for a submission.
    Priority:
      1. submission.payload_text (if non-empty)
      2. prompt.text (if available)
      3. None
    """
    if submission and submission.payload_text and submission.payload_text.strip() != "":
        return submission.payload_text
    if prompt and prompt.text:
        return prompt.text
    return None
