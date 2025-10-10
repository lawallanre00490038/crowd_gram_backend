from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, Query
from datetime import datetime

from src.db.models import  Status
from src.db.database import get_session
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
    DailyStatsResponse
)


router = APIRouter()



ALLOWED_STATUSES = [
    Status.pending, 
    Status.accepted, 
    Status.rejected,
    Status.approved,
    Status.assigned
]


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
