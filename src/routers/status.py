from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime
from typing import List, Optional
from src.db.models import ProjectAllocation, ReviewerAllocation, Submission, User 

from src.db.models import  Status
from src.db.database import get_session
from src.utils.status_utils import get_allocations_by_status
from src.utils.analytics import (
    get_contributor_stats,
    get_reviewer_stats,
    get_platform_stats,
    get_daily_stats,
)
from src.schemas.status import (
    ContributorStats, 
    ReviewerStats, 
    PlatformStats, 
    DailyStatsResponse,
    ProjectAllocationResponse
)


router = APIRouter()



ALLOWED_STATUSES = [
    Status.pending, 
    Status.accepted, 
    Status.rejected,
    Status.approved,
    Status.assigned
]

# ------------------------
# Routes
# ------------------------
@router.get("/allocations", response_model=List[ProjectAllocationResponse])
async def get_allocations(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    email: Optional[str] = Query(None, description="Filter by user email"),
    status: Optional[List[Status]] = Query([Status.pending], description="Filter by status(es)"),
    reviewer: Optional[bool] = Query(False, description="If true, fetch reviewer allocations"),
    session: AsyncSession = Depends(get_session)
):
    """
    Fetch allocations filtered dynamically by user_id, email, and/or status.
    If reviewer=True, fetch reviewer allocations instead of contributor allocations.
    """
    # Validate statuses
    for s in status:
        if s not in ALLOWED_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Status must be one of: {[s.value for s in ALLOWED_STATUSES]}"
            )

    if reviewer:
        query = select(ReviewerAllocation).options(
            selectinload(ReviewerAllocation.submission)
            .selectinload(Submission.task),
            selectinload(ReviewerAllocation.submission)
            .selectinload(Submission.assignment)
        )
        if user_id:
            query = query.where(ReviewerAllocation.reviewer_id == user_id)
        if email:
            # join with user table to filter by email
            query = query.join(ReviewerAllocation.reviewer).where(User.email == email)
        if status:
            query = query.where(ReviewerAllocation.status.in_([s.value for s in status]))

        result = await session.execute(query)
        allocations = result.scalars().all()
        # Transform for response model
        response = [
            ProjectAllocationResponse(
                id=a.id,
                user_id=a.reviewer_id,
                user_email=a.reviewer.email if a.reviewer else None,
                task_id=a.submission.task_id if a.submission else None,
                project_id=a.submission.assignment.project_id if a.submission and a.submission.assignment else None,
                status=a.status,
                assigned_at=a.assigned_at
            )
            for a in allocations
        ]
        return response

    else:
        query = select(ProjectAllocation).options(selectinload(ProjectAllocation.project))
        if user_id:
            query = query.where(ProjectAllocation.user_id == user_id)
        if email:
            query = query.join(ProjectAllocation.user).where(User.email == email)
        if status:
            query = query.where(ProjectAllocation.status.in_([s.value for s in status]))

        result = await session.execute(query)
        allocations = result.scalars().all()
        return allocations


# -------------------Analytics Routes---------------------

@router.get(
    "/contributor/{email}",
    response_model=ContributorStats,
    summary="Contributor Stats",
    description="Get statistics for a specific contributor across all task types.",
)
async def contributor_stats(
    email: str,
    start: datetime = Query(None, description="Filter start datetime"),
    end: datetime = Query(None, description="Filter end datetime"),
    session: AsyncSession = Depends(get_session),
):
    return await get_contributor_stats(session, email, start, end)


@router.get(
    "/reviewer/{email}",
    response_model=ReviewerStats,
    summary="Reviewer Stats",
    description="Get statistics for a specific reviewer.",
)
async def reviewer_stats(
    email: str,
    start: datetime = Query(None, description="Filter start datetime"),
    end: datetime = Query(None, description="Filter end datetime"),
    session: AsyncSession = Depends(get_session),
):
    return await get_reviewer_stats(session, email, start, end)


@router.get(
    "/platform/analytics",
    response_model=PlatformStats,
    summary="Platform Stats",
    description="Get overall statistics across the entire platform.",
)
async def platform_stats(session: AsyncSession = Depends(get_session)):
    print("Fetching platform stats...")
    return await get_platform_stats(session)


@router.get(
    "/daily/analytics",
    response_model=DailyStatsResponse,
    summary="Daily Stats",
    description="Get daily submission statistics for the last N days.",
)
async def daily_stats(
    days: int = Query(7, description="Number of past days to include"),
    session: AsyncSession = Depends(get_session),
):
    return {"data": await get_daily_stats(session, days)}
