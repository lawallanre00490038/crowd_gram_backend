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

    # Prompt details
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

    # Contributor submission
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

    # Reviewer details (all allocations)
    reviewers_info: List[ReviewerInfo] = []
    if submission and submission.review_allocations:
        for ra in submission.review_allocations:
            # Find review for this reviewer
            reviewer_review = next((r for r in submission.reviews if r.reviewer_id == ra.reviewer_id), None)
            # Find payment for this reviewer-task pair
            reviewer_payment = payment if payment and payment.user_id == ra.reviewer_id else None

            reviewers_info.append(ReviewerInfo(
                reviewer_id=ra.reviewer_id,
                reviewer_email=ra.reviewer.email if ra.reviewer else None,
                review_scores=reviewer_review.scores if reviewer_review else None,
                review_total_score=reviewer_review.total_score if reviewer_review else None,
                review_decision=reviewer_review.decision.value if reviewer_review and reviewer_review.decision else ra.status.value,
                review_comments=reviewer_review.comments if reviewer_review else None,
                total_coins_earned=reviewer_payment.coins_earned if reviewer_payment else 0
            ))

    review_info = ReviewInfo(reviewers=reviewers_info) if reviewers_info else None

    return TaskWithDetails(
        task_id=task.id,
        assignment_id=alloc.id if alloc else (rev_alloc.id if rev_alloc else None),
        assigned_at=alloc.assigned_at if alloc else (rev_alloc.assigned_at if rev_alloc else None),
        status=alloc.status.value if alloc else (rev_alloc.status.value if rev_alloc else None),
        prompt=prompt_info,
        submission=submission_info,
        review=review_info
    )






# async def build_task_details(
#     task: Task,
#     alloc: Optional[ProjectAllocation] = None,
#     submission: Optional[Submission] = None,
#     rev_alloc: Optional[ReviewerAllocation] = None,
#     review: Optional[Review] = None,
#     payment: Optional[CoinPayment] = None,
#     user_email: Optional[str] = None
# ) -> TaskWithDetails:

#     prompt_info = PromptInfo(
#         prompt_id=task.prompt.id if task.prompt else None,
#         sentence_id=task.prompt.id if task.prompt else None,
#         sentence_text=task.prompt.text if task.prompt else None,
#         media_url=task.prompt.media_url if task.prompt else None,
#         category=task.prompt.category if task.prompt else None,
#         domain=task.prompt.domain if task.prompt else None,
#         max_reuses=task.prompt.max_reuses if task.prompt else None,
#         current_reuses=task.prompt.current_reuses if task.prompt else None
#     ) if task.prompt else None

#     submission_info = SubmissionInfo(
#         submission_id=submission.id,
#         user_id=submission.user_id,
#         user_email=user_email,
#         type=submission.type,
#         payload_text=submission.payload_text,
#         file_url=submission.file_url,
#         status=submission.status.value,
#         created_at=submission.created_at,
#         updated_at=submission.updated_at
#     ) if submission else None

#     review_info = ReviewInfo(
#         review_scores=review.scores if review else None,
#         review_total_score=review.total_score if review else None,
#         review_decision=review.decision.value if review and review.decision else None,
#         review_comments=review.comments if review else None,
#         total_coins_earned=payment.coins_earned if payment else 0
#     ) if rev_alloc else None

#     return TaskWithDetails(
#         task_id=task.id,
#         assignment_id=alloc.id if alloc else (rev_alloc.id if rev_alloc else None),
#         assigned_at=alloc.assigned_at if alloc else (rev_alloc.assigned_at if rev_alloc else None),
#         status=alloc.status.value if alloc else (rev_alloc.status.value if rev_alloc else None),
#         prompt=prompt_info,
#         submission=submission_info,
#         review=review_info
#     )

