from typing import Optional, List
from src.schemas.project_schemas import TaskWithDetails, PromptInfo, SubmissionInfo, ReviewInfo, ReviewerInfo
from src.db.models import Task, ProjectAllocation, Submission, ReviewerAllocation, Review, CoinPayment


async def build_task_details(
    task: Task,
    alloc: Optional[ProjectAllocation] = None,
    submission: Optional[Submission] = None,
    rev_alloc: Optional[ReviewerAllocation] = None,
    review: Optional[Review] = None,
    payment: Optional[CoinPayment] = None,
    user_email: Optional[str] = None
) -> TaskWithDetails:

    prompt_info = PromptInfo(
        prompt_id=task.prompt.id if task.prompt else None,
        sentence_id=task.prompt.id if task.prompt else None,
        sentence_text=task.prompt.text if task.prompt else None,
        media_url=task.prompt.media_url if task.prompt else None,
        category=task.prompt.category if task.prompt else None,
        domain=task.prompt.domain if task.prompt else None,
        max_reuses=task.prompt.max_reuses if task.prompt else None,
        current_reuses=task.prompt.current_reuses if task.prompt else None
    ) if task.prompt else None

    submission_info = SubmissionInfo(
        submission_id=submission.id,
        user_id=submission.user_id,
        user_email=user_email,
        type=submission.type,
        payload_text=submission.payload_text,
        file_url=submission.file_url,
        status=submission.status.value,
        created_at=submission.created_at,
        updated_at=submission.updated_at
    ) if submission else None

    review_info = ReviewInfo(
        review_scores=review.scores if review else None,
        review_total_score=review.total_score if review else None,
        review_decision=review.decision.value if review and review.decision else None,
        review_comments=review.comments if review else None,
        total_coins_earned=payment.coins_earned if payment else 0
    ) if rev_alloc else None

    return TaskWithDetails(
        task_id=task.id,
        assignment_id=alloc.id if alloc else (rev_alloc.id if rev_alloc else None),
        assigned_at=alloc.assigned_at if alloc else (rev_alloc.assigned_at if rev_alloc else None),
        status=alloc.status.value if alloc else (rev_alloc.status.value if rev_alloc else None),
        prompt=prompt_info,
        submission=submission_info,
        review=review_info
    )
