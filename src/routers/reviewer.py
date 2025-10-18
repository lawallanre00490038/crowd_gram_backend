import io
import pandas as pd
from datetime import datetime
from io import BytesIO
from typing import List, Optional, Dict
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Body, Query
from sqlmodel import Session, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


from src.db.database import get_session
from src.services.coins import award_coins_on_accept, award_reviewer_payment  
from src.db.models import (
  ReviewerAllocation, 
  Submission, 
  User, 
  Status,
  Review,
  Project,
  AgentAllocation,
  Task,
)
from src.schemas.reviewer_schema import (
    FilterReviewResponse,
    ReviewerHistoryResponse
)
from src.utils.read_file import read_uploaded_dataframe

router = APIRouter()
ALLOWED_STATUSES = [Status.pending, Status.accepted, Status.rejected, Status.redo]


@router.post("/assign_submission_to_reviewer/")
async def assign_submission_to_reviewer(
    project_id: str,
    submission_id: str,
    reviewer_identifier: str = Query(..., description="Reviewer ID or email"),
    session: AsyncSession = Depends(get_session)
):
    """
    Assign a single submission to a reviewer.

    Flow:
    1. Check if the submission is already assigned to this reviewer.
    2. If not assigned, create a ReviewerAllocation with status "pending".
    3. Commit to the database and return the allocation object.

    Parameters:
    - submission_id (str): ID of the submission to assign.
    - reviewer_id (str): ID of the reviewer to assign the submission to.
    - session (AsyncSession, dependency): Async database session.

    Returns:
    - ReviewerAllocation object containing allocation ID, submission ID, reviewer ID, status, and assigned_at timestamp.

    Raises:
    - HTTPException 400: If the submission is already assigned to the reviewer.
    """
    # 1️⃣ Resolve reviewer (by ID or email) with async-safe query
    reviewer_result = await session.execute(
        select(User).where(
            (User.id == reviewer_identifier) | (User.email == reviewer_identifier)
        )
    )
    reviewer = reviewer_result.scalars().first()
    if not reviewer:
        raise HTTPException(status_code=404, detail="Reviewer not found")
    reviewer_id = reviewer.id

    # 2️⃣ Load submission with its task to avoid lazy loading
    sub_result = await session.execute(
        select(Submission)
        .options(selectinload(Submission.task))  # eager load task
        .where(Submission.id == submission_id)
    )
    submission = sub_result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Check project association
    if not submission.task or submission.task.project_id != project_id:
        raise HTTPException(status_code=400, detail="Submission does not belong to this project")

    # 3️⃣ Check if allocation already exists and is not rejected
    existing_result = await session.execute(
        select(ReviewerAllocation)
        .options(selectinload(ReviewerAllocation.reviewer))
        .where(
            ReviewerAllocation.submission_id == submission_id,
            ReviewerAllocation.status != Status.rejected
        )
    )
    existing = existing_result.scalars().first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"This submission {submission_id} is already assigned to the reviewer {existing.reviewer.email} and not rejected"
        )

    # 4️⃣ Create new allocation
    allocation = ReviewerAllocation(
        submission_id=submission_id,
        reviewer_id=reviewer_id,
        status=Status.pending,
        assigned_at=datetime.utcnow()
    )
    session.add(allocation)
    await session.commit()
    await session.refresh(allocation)

    return allocation



@router.post("/upload_reviewer_allocations/")
async def upload_reviewer_allocations(
    project_id: str,
    file: UploadFile,
    session: AsyncSession = Depends(get_session)
):
    """
    Bulk upload reviewer allocations from an Excel file.

    Flow:
    1. Read the uploaded Excel file.
    2. Validate that required columns "submission_id" and "reviewer_email" exist.
    3. For each row:
       - Retrieve reviewer by email.
       - Retrieve submission by ID.
       - Create a ReviewerAllocation with status "pending" and optional assigned_at timestamp.
    4. Commit all allocations to the database.
    5. Return summary of uploaded allocations.

    Parameters:
    - file (UploadFile): Excel file containing columns "submission_id" and "reviewer_email".
    - session (AsyncSession, dependency): Async database session.

    Returns:
    - dict: {"uploaded": int, "details": List[str]} with the number of allocations uploaded and their IDs.

    Raises:
    - HTTPException 400: If required columns are missing.
    - HTTPException 404: If a reviewer email or submission ID does not exist.
    """

    df = await read_uploaded_dataframe(file, required_cols={"submission_id", "reviewer_email"})

    
    required_cols = {"submission_id", "reviewer_email"}
    if not required_cols.issubset(df.columns):
        raise HTTPException(status_code=400, detail=f"Excel must have {required_cols}")

    # ✅ Pre-fetch reviewers into dict
    reviewer_emails = df["reviewer_email"].dropna().unique().tolist()
    result = await session.execute(select(User).where(User.email.in_(reviewer_emails)))
    reviewers = {u.email: u for u in result.scalars().all()}

    # ✅ Pre-fetch submissions into dict
    submission_ids = df["submission_id"].dropna().unique().tolist()
    sub_result = await session.execute(
        select(Submission).where(
            Submission.id.in_(submission_ids),
            Submission.task.has(Project.id == project_id)  # ensures submission belongs to project
        )
    )
    submissions = {s.id: s for s in sub_result.scalars().all()}

    allocations = []
    skipped = []

    for _, row in df.iterrows():
        reviewer_email = row["reviewer_email"]
        submission_id = row["submission_id"]

        reviewer = reviewers.get(reviewer_email)
        submission = submissions.get(submission_id)

        if not reviewer:
            skipped.append(f"Reviewer {reviewer_email} not found")
            continue
        if not submission:
            skipped.append(f"Submission {submission_id} invalid for project {project_id}")
            continue

        # Skip duplicate if exists and not rejected
        existing_result = await session.execute(
            select(ReviewerAllocation)
            .options(selectinload(ReviewerAllocation.reviewer))
            .where(
                ReviewerAllocation.submission_id == submission.id,
                ReviewerAllocation.status != Status.rejected
            )
        )
        existing = existing_result.scalars().first()

        if existing:
            reviewer_email_assigned = (
                existing.reviewer.email if existing.reviewer else "unknown"
            )
            skipped.append(
                f"❌ Submission {submission_id} is already assigned to reviewer "
                f"{reviewer_email_assigned} (cannot reassign unless rejected)"
            )
            continue

        assigned_at = (
            row["assigned_at"] if "assigned_at" in df.columns and pd.notna(row["assigned_at"])
            else datetime.utcnow()
        )

        allocation = ReviewerAllocation(
            submission_id=submission.id,
            reviewer_id=reviewer.id,
            status=Status.pending,
            assigned_at=assigned_at
        )
        session.add(allocation)
        allocations.append(allocation)

    await session.commit()

    return {
        "uploaded": len(allocations),
        "skipped": skipped,
        "details": [a.id for a in allocations]
    }





# ---------------------------
# REVIEW SUBMISSION
# ---------------------------

@router.post("/submissions/{submission_id}/review")
async def review_submission(
    project_id: str,
    submission_id: str,
    scores: Dict[str, int],
    reviewer_identifier: str = Query(..., description="Reviewer ID or email"),
    comments: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    """
        Review a submission, calculate scores, and approve/reject.

        **Flow**:
        1. Retrieve submission and associated project.
        2. Compute `total_score` based on `review_parameters` and reviewer scores.
        3. Determine approval by comparing total score with project threshold.
        4. Update submission status to `approved` or `rejected`.
        5. Create a `Review` record for tracking.
        6. Update `AgentAllocation` and mark `completed_at`.
        7. Award coins to submitter if approved.
        8. Award payment to reviewer.

        Args:
            submission_id (str): ID of the submission being reviewed.
            reviewer_id (str): ID of the reviewer performing the review.
            scores (Dict[str, int]): Scores for each review parameter (e.g., {"accuracy": 4, "clarity": 5}).
            comments (Optional[str]): Optional textual feedback from reviewer.
            session (Session): Database session dependency.

        Returns:
            Dict[str, Any]: Contains submission status, total score, and approval boolean.

        Raises:
            HTTPException: 404 if submission or project does not exist.

        Notes:
            - Supports multi-parameter scoring.
            - Automatically updates the submitter’s allocation and awards coins if approved.
            - Review is recorded for audit and analytics purposes.
    """
    # 1️⃣ Resolve reviewer (accept ID or email)
    reviewer_query = select(User).where(
        (User.id == reviewer_identifier) | (User.email == reviewer_identifier)
    )
    reviewer_result = await session.execute(reviewer_query)
    reviewer = reviewer_result.scalars().first()

    if not reviewer:
        raise HTTPException(status_code=404, detail="Reviewer not found")
    reviewer_id = reviewer.id  # ensure we use the actual ID internally

    # 1️⃣ Fetch submission with project and allocation
    result = await session.execute(
        select(Submission)
        .where(Submission.id == submission_id)
        .options(
            selectinload(Submission.task).selectinload(Task.project),
            selectinload(Submission.allocation).selectinload(AgentAllocation.project),
        )
    )
    submission = result.scalars().first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    project = submission.task.project if submission.task else None
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not submission.task or submission.task.project_id != project_id:
        raise HTTPException(status_code=400, detail="Submission does not belong to this project")

    # 2️⃣ Determine review parameters dynamically
    review_params = project.review_parameters or list(scores.keys())
    if not review_params:
        review_params = list(scores.keys())

    # 3️⃣ Calculate total score
    total_score = sum([scores.get(param, 0) for param in review_params])
    max_score = len(review_params) * (project.review_scale or 5)
    threshold_score = project.review_threshold_percent / 100 * max_score
    approved = total_score >= threshold_score
    scored_percent = (total_score / max_score * 100) if max_score else 0


    # 4️⃣ Update submission status
    if not submission.meta:
        submission.meta = {}

    if not approved:
        # Increment redo_count
        submission.meta["redo_count"] = submission.meta.get("redo_count", 0) + 1

        # Check if redo allowed
        if project.num_redo is None or submission.meta["redo_count"] <= project.num_redo:
            submission.status = Status.redo
        else:
            submission.status = Status.rejected
    else:
        submission.status = Status.accepted

    session.add(submission)


    # 5️⃣ Create or update review record
    existing_review_result = await session.execute(
        select(Review)
        .where(
            Review.submission_id == submission.id,
            Review.reviewer_id == reviewer_id
        )
    )
    review = existing_review_result.scalars().first()
    if review:
        # update existing review
        review.scores = scores
        review.total_score = total_score
        review.decision = submission.status
        review.approved = approved
        review.comments = comments
    else:
        # create new review
        review = Review(
            submission_id=submission.id,
            reviewer_id=reviewer_id,
            review_level="human",
            scores=scores,
            total_score=total_score,
            decision=submission.status,
            approved=approved,
            comments=comments,
        )
    session.add(review)

    # 6️⃣ Update AgentAllocation if exists
    if submission.allocation:
        alloc = submission.allocation
        alloc.status = submission.status
        alloc.completed_at = datetime.utcnow()
        session.add(alloc)

    # 7️⃣ Update ReviewerAllocation if exists
    result_review_alloc = await session.execute(
        select(ReviewerAllocation)
        .where(
            ReviewerAllocation.submission_id == submission.id,
            ReviewerAllocation.reviewer_id == reviewer_id
        )
    )
    review_allocation = result_review_alloc.scalars().first()
    if review_allocation:
        review_allocation.status = submission.status
        review_allocation.reviewed_at = datetime.utcnow()
        session.add(review_allocation)

    # 8️⃣ Commit all changes
    await session.commit()
    await session.refresh(submission)


    # ------------------------------
    # 9️⃣ Award coins (one-time per submission)
    # ------------------------------
    if submission.status == Status.accepted:
        await award_coins_on_accept(session, submission)

    await award_reviewer_payment(session, reviewer_id, submission.id)


    return {
        "submission_status": submission.status,
        "total_score": total_score,
        "approved": approved,
        "project_review_threshold": project.review_threshold_percent,
        "scored_percent": scored_percent
    }



@router.patch("/update/{submission_id}/review", response_model=Submission)
async def reviewer_review_submission(
    project_id: str,
    submission_id: str,
    status: Status = Query(Status.pending, description="Status of review"),
    reviewer_identifier: str = Query(..., description="Reviewer ID or email"),
    comments: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    """
    Reviewer endpoint: approve/reject/update submissions.

    - Accepts reviewer ID or email to identify the reviewer.
    - Allowed statuses: accepted, rejected, redo, or pending.
    - Updates submission, allocations, and records review.
    - Triggers coin awards if accepted.
    """

    if status not in ALLOWED_STATUSES:
        raise HTTPException(
            status_code=400,
            detail="Reviewer can only set status to accepted, rejected, redo, or pending",
        )

    reviewer_query = select(User).where(
        (User.id == reviewer_identifier) | (User.email == reviewer_identifier)
    )
    reviewer_result = await session.execute(reviewer_query)
    reviewer = reviewer_result.scalars().first()
    if not reviewer:
        raise HTTPException(status_code=404, detail="Reviewer not found")
    reviewer_id = reviewer.id

    result = await session.execute(
        select(Submission)
        .where(Submission.id == submission_id)
        .options(
            selectinload(Submission.task),
            selectinload(Submission.allocation)
        )
    )
    submission = result.scalars().first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    if not submission.task:
        raise HTTPException(status_code=400, detail="Submission missing associated task")

    if submission.task.project_id != project_id:
        raise HTTPException(status_code=400, detail="Submission does not belong to this project")

    submission.status = status

    existing_review_result = await session.execute(
        select(Review).where(
            Review.submission_id == submission.id,
            Review.reviewer_id == reviewer_id
        )
    )
    review = existing_review_result.scalars().first()
    if review:
        review.decision = status
        review.comments = comments
    else:
        review = Review(
            submission_id=submission.id,
            reviewer_id=reviewer_id,
            review_level="human",
            decision=status,
            comments=comments,
        )
    session.add(review)

    if submission.allocation:
        alloc = submission.allocation
        alloc.status = status
        alloc.completed_at = datetime.utcnow()
        session.add(alloc)

    result_review_alloc = await session.execute(
        select(ReviewerAllocation)
        .where(
            ReviewerAllocation.submission_id == submission.id,
            ReviewerAllocation.reviewer_id == reviewer_id
        )
    )
    review_alloc = result_review_alloc.scalars().first()
    if review_alloc:
        review_alloc.status = status
        review_alloc.reviewed_at = datetime.utcnow()
        session.add(review_alloc)

    if status == Status.accepted:
        await award_coins_on_accept(session, submission)
        await award_reviewer_payment(session, reviewer_id, submission.id)

    session.add(submission)
    await session.commit()
    await session.refresh(submission)
    return submission






# ----------------------------
# Filter Reviews
# ----------------------------
@router.get(
    "/{reviewer_identifier}/filter", 
    response_model=List[FilterReviewResponse]
)
async def get_reviewer_filtered_reviews(
    reviewer_identifier: str,
    project_id: Optional[str] = None,
    status: Optional[List[Status]] = Query([Status.pending], description="Filter by status(es)"),
    session: AsyncSession = Depends(get_session)
):
    """
    Retrieve submissions assigned to a reviewer filtered by status.

    Parameters:
    - reviewer_id (str): ID of the reviewer
    - status (List[Status], optional): Filter by one or more statuses (default: pending)
    - session (AsyncSession): DB session

    Returns:
    - List[ReviewResponse]: Each submission with reviewer allocation info, prompt, file URL, contributor, and status
    """
    reviewer_query = select(User).where(
        (User.id == reviewer_identifier) | (User.email == reviewer_identifier)
    )
    reviewer_result = await session.execute(reviewer_query)
    reviewer = reviewer_result.scalars().first()
    if not reviewer:
        raise HTTPException(status_code=404, detail="Reviewer not found")

    reviewer_id = reviewer.id 

    for s in status:
        if s not in ALLOWED_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Status must be one of: {[s.value for s in ALLOWED_STATUSES]}"
            )

    query = select(ReviewerAllocation).where(ReviewerAllocation.reviewer_id == reviewer_id)
    if status:
        query = query.where(ReviewerAllocation.status.in_([Status(s).value for s in status]))
    if project_id:
        query = query.join(ReviewerAllocation.submission).where(Submission.task.has(Task.project_id == project_id))
    query = query.options(
        selectinload(ReviewerAllocation.submission)
            .selectinload(Submission.task)
            .selectinload(Task.prompt),  # preload prompt to avoid sync lazy load
        selectinload(ReviewerAllocation.submission)
            .selectinload(Submission.allocation)
    )

    result = await session.execute(query)
    allocations = result.scalars().all()

    response = []
    for alloc in allocations:
        sub = alloc.submission
        if not sub or not sub.task:
            continue  # skip incomplete data
        response.append(FilterReviewResponse(
            reviewer_allocation_id=alloc.id,
            submission_id=sub.id,
            sentence_id=sub.task.prompt_id,
            prompt=sub.task.prompt.text if sub.task.prompt else None,
            file_url=sub.file_url,
            payload_text=sub.payload_text,
            contributor_id=sub.user_id,
            assigned_at=alloc.assigned_at,
            status=alloc.status
        ))
    return response





# ----------------------------
# Reviewer History
# ----------------------------
@router.get(
    "/{reviewer_identifier}/history",
    response_model=List[ReviewerHistoryResponse]
)
async def get_reviewer_history(
    reviewer_identifier: str,
    project_id: Optional[str] = None,
    session: AsyncSession = Depends(get_session)
):
    """
    Retrieve all historical submissions assigned to a reviewer.

    Flow:
    1. Query all ReviewerAllocation entries for the reviewer.
    2. Load related Submission and Task details.
    3. Return submission ID, sentence ID, prompt, contributor ID, status, and reviewed_at timestamp.

    Parameters:
    - reviewer_id (str, path): ID of the reviewer.
    - session (AsyncSession, dependency): Async database session.

    Returns:
    - List[Dict]: Each dict includes submission_id, sentence_id (prompt ID), prompt, contributor_id, status, and reviewed_at timestamp.
    """
     # 1️⃣ Resolve reviewer by ID or email
    reviewer_query = select(User).where(
        (User.id == reviewer_identifier) | (User.email == reviewer_identifier)
    )
    reviewer_result = await session.execute(reviewer_query)
    reviewer = reviewer_result.scalars().first()
    if not reviewer:
        raise HTTPException(status_code=404, detail="Reviewer not found")

    reviewer_id = reviewer.id


    # 2️⃣ Build query with eager loading
    query = (
        select(ReviewerAllocation)
        .where(ReviewerAllocation.reviewer_id == reviewer_id)
        .options(
            selectinload(ReviewerAllocation.submission)
            .selectinload(Submission.task)
            .selectinload(Task.prompt)  # preload prompt to avoid sync lazy-load
        )
    )

    # 3️⃣ Filter by project if provided
    if project_id:
        query = query.join(ReviewerAllocation.submission).where(
            Submission.task.has(Task.project_id == project_id)
        )

    # 4️⃣ Execute query
    result = await session.execute(query)
    allocations = result.scalars().all()

    # 5️⃣ Build response
    response = []
    for alloc in allocations:
        sub = alloc.submission
        if not sub or not sub.task:
            continue
        response.append(ReviewerHistoryResponse(
            submission_id=sub.id,
            sentence_id=sub.task.prompt_id,
            prompt=sub.task.prompt.text if sub.task.prompt else None,
            reviewer_id=sub.user_id,
            status=alloc.status,
            reviewed_at=alloc.reviewed_at
        ))

    return response
