from datetime import datetime, timedelta
from fastapi import HTTPException
from typing import List
from sqlmodel import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from src.schemas.status import (
    ContributorStats,
)
from sqlalchemy.orm import selectinload
from src.db.models import ProjectAllocation

from src.db.models import (
    User,
    Project,
    ProjectAllocation,
    Submission,
    CoinPayment,
    Status,
    TaskType,
    Review,
    ReviewerAllocation,
)


# ------------------- CONTRIBUTOR STATS -------------------
async def get_contributor_stats(
    session: AsyncSession, email: str, start: datetime = None, end: datetime = None
):
    """Return stats for a contributor across all task types (looked up by email)."""

    # Step 1: Find user by email
    user_result = await session.execute(select(User).where(User.email == email))
    user = user_result.scalar_one_or_none()
    if not user:
        return {"error": f"No user found with email {email}"}

    # Step 2a: Submissions (with assignment + project eager loaded)
    sub_query = (
        select(Submission)
        .where(Submission.user_id == user.id)
        .options(
            selectinload(Submission.assignment).selectinload(ProjectAllocation.project)
        )
    )
    if start:
        sub_query = sub_query.where(Submission.created_at >= start)
    if end:
        sub_query = sub_query.where(Submission.created_at <= end)

    submissions: List[Submission] = (await session.execute(sub_query)).scalars().all()

    # Step 2b: Allocations (with project eager loaded)
    alloc_query = (
        select(ProjectAllocation)
        .where(ProjectAllocation.user_id == user.id)
        .options(selectinload(ProjectAllocation.project))
    )
    allocations: List[ProjectAllocation] = (await session.execute(alloc_query)).scalars().all()

    # Step 3: Overall submission stats
    total = len(submissions)
    approved = sum(1 for s in submissions if s.status == Status.accepted)
    pending = sum(1 for s in submissions if s.status == Status.submitted)
    rejected = sum(1 for s in submissions if s.status == Status.rejected)

    # Step 4: Coins earned
    coin_query = select(CoinPayment).where(CoinPayment.user_id == user.id)
    coin_payments: List[CoinPayment] = (await session.execute(coin_query)).scalars().all()

    # Step 5: Per-project stats
    project_stats = {}

    # Initialize all projects from allocations and submissions
    for item in allocations + [s.assignment for s in submissions if s.assignment]:
        if not item or not item.project:
            continue
        project = item.project
        key = project.id
        if key not in project_stats:
            project_stats[key] = {
                "project_id": project.id,
                "project_name": project.name,
                "number_assigned": 0,
                "total": 0,
                "approved": 0,
                "rejected": 0,
                "pending": 0,
                "total_submissions": 0,
                "total_coins_earned": 0,
                "total_amount_earned": 0,  # NEW
                "agent_amount": project.agent_amount,  # store for calculation
            }

    # Submissions contribute to totals
    for sub in submissions:
        alloc = sub.assignment
        if not alloc or not alloc.project:
            continue
        key = alloc.project.id
        project_stats[key]["total"] += 1
        if sub.status == Status.accepted:
            project_stats[key]["approved"] += 1
        elif sub.status == Status.rejected:
            project_stats[key]["rejected"] += 1
        elif sub.status == Status.submitted:
            project_stats[key]["pending"] += 1

    # Allocations contribute to number assigned
    for alloc in allocations:
        if not alloc.project:
            continue
        key = alloc.project.id
        project_stats[key]["number_assigned"] += 1

    # Fill total_submissions, total_coins_earned, and total_amount_earned per project
    for key, stats in project_stats.items():
        stats["total_submissions"] = sum(
            1 for s in submissions if s.assignment and s.assignment.project.id == key
        )
        stats["total_coins_earned"] = sum(
            c.coins_earned for c in coin_payments if c.project_id == key
        )
        stats["total_amount_earned"] = stats["total_coins_earned"] * stats["agent_amount"]

        # Optional: remove agent_amount from final output if you don't want it
        del stats["agent_amount"]

    return {
        "user_email": email,
        "approved": approved,
        "pending": pending,
        "rejected": rejected,
        "per_project": list(project_stats.values()),
    }
# ------------------- CONTRIBUTOR STATS -------------------



# ------------------- REVIEWER STATS -------------------
# ------------------- REVIEWER STATS (Corrected) -------------------
async def get_reviewer_stats(session: AsyncSession, email: str, start: datetime = None, end: datetime = None):
    """Return stats for a reviewer (looked up by email)."""

    reviewer_result = await session.execute(select(User).where(User.email == email))
    reviewer = reviewer_result.scalar_one_or_none()
    if not reviewer:
        raise HTTPException(status_code=404, detail=f"No reviewer found with email {email}")

    # 1. Fetch Allocations
    alloc_query = (
        select(ReviewerAllocation)
        .where(ReviewerAllocation.reviewer_id == reviewer.id)
        .options(
            selectinload(ReviewerAllocation.submission)
            .selectinload(Submission.assignment)
            .selectinload(ProjectAllocation.project)
        )
    )
    if start:
        alloc_query = alloc_query.where(ReviewerAllocation.assigned_at >= start)
    if end:
        alloc_query = alloc_query.where(ReviewerAllocation.assigned_at <= end)
    allocations: List[ReviewerAllocation] = (await session.execute(alloc_query)).scalars().all()

    # 2. Fetch Reviews
    review_query = (
        select(Review)
        .where(Review.reviewer_id == reviewer.id)
        .options(
            selectinload(Review.submission)
            .selectinload(Submission.assignment)
            .selectinload(ProjectAllocation.project)
        )
    )
    if start:
        review_query = review_query.where(Review.created_at >= start)
    if end:
        review_query = review_query.where(Review.created_at <= end)
    reviews: List[Review] = (await session.execute(review_query)).scalars().all()

    # 3. Fetch Coin Payments
    coin_query = select(CoinPayment).where(CoinPayment.user_id == reviewer.id)
    coin_payments: List[CoinPayment] = (await session.execute(coin_query)).scalars().all()

    # --- Aggregate Stats ---
    total_reviewed = len(reviews)
    approved = sum(1 for r in reviews if r.decision == Status.accepted)
    rejected = sum(1 for r in reviews if r.decision == Status.rejected)
    # FIX 1: Calculate the number of pending reviews
    pending = total_reviewed - (approved + rejected)

    # --- Per-project stats ---
    project_stats = {}

    all_related_items = allocations + [r.submission for r in reviews if r.submission]
    for item in all_related_items:
        project = item.submission.assignment.project if hasattr(item, 'submission') and item.submission and item.submission.assignment else None
        if not project:
            continue
        
        key = project.id
        if key not in project_stats:
            project_stats[key] = {
                "project_id": project.id,
                "project_name": project.name,
                "number_assigned": 0,
                "total_reviewed": 0,
                "approved": 0,
                "rejected": 0,
                "pending": 0,  # FIX 2: Ensure 'pending' is in the project dictionary
                "total_coins_earned": 0,
                "total_amount_earned": 0,
                "reviewer_amount": project.reviewer_amount,
            }

    for alloc in allocations:
        project = alloc.submission.assignment.project if alloc.submission and alloc.submission.assignment else None
        if project and project.id in project_stats:
            project_stats[project.id]["number_assigned"] += 1

    for review in reviews:
        project = review.submission.assignment.project if review.submission and review.submission.assignment else None
        if project and project.id in project_stats:
            stats = project_stats[project.id]
            stats["total_reviewed"] += 1
            if review.decision == Status.accepted:
                stats["approved"] += 1
            elif review.decision == Status.rejected:
                stats["rejected"] += 1
            else:
                # FIX 3: Increment the per-project pending count
                stats["pending"] += 1

    for key, stats in project_stats.items():
        stats["total_coins_earned"] = sum(c.coins_earned for c in coin_payments if c.project_id == key)
        stats["total_amount_earned"] = stats["total_coins_earned"] * stats["reviewer_amount"]
        del stats["reviewer_amount"]

    # FIX 4: Add the missing 'pending_reviews' field to the final response
    return {
        "reviewer_email": email,
        "total_reviewed": total_reviewed,
        "approved_reviews": approved,
        "rejected_reviews": rejected,
        "pending_reviews": pending, # This field was missing
        "per_project": list(project_stats.values()),
    }



# async def get_reviewer_stats(session: AsyncSession, email: str, start: datetime = None, end: datetime = None):
#     """Return stats for a reviewer (looked up by email)."""

#     reviewer_result = await session.execute(select(User).where(User.email == email))
#     reviewer = reviewer_result.scalar_one_or_none()
#     if not reviewer:
#         return {"error": f"No reviewer found with email {email}"}

#     # 1️⃣ Number of review tasks assigned
#     alloc_query = (
#         select(ReviewerAllocation)
#         .where(ReviewerAllocation.reviewer_id == reviewer.id)
#         .options(
#             selectinload(ReviewerAllocation.submission)
#             .selectinload(Submission.assignment)
#             .selectinload(ProjectAllocation.project)
#         )
#     )
#     if start:
#         alloc_query = alloc_query.where(ReviewerAllocation.assigned_at >= start)
#     if end:
#         alloc_query = alloc_query.where(ReviewerAllocation.assigned_at <= end)

#     allocations: List[ReviewerAllocation] = (await session.execute(alloc_query)).scalars().all()

#     # 2️⃣ Reviews actually completed
#     review_query = (
#         select(Review)
#         .where(Review.reviewer_id == reviewer.id)
#         .options(
#             selectinload(Review.submission)
#             .selectinload(Submission.assignment)
#             .selectinload(ProjectAllocation.project)
#         )
#     )
#     if start:
#         review_query = review_query.where(Review.created_at >= start)
#     if end:
#         review_query = review_query.where(Review.created_at <= end)

#     reviews: List[Review] = (await session.execute(review_query)).scalars().all()

#     total_reviewed = len(reviews)
#     approved = sum(1 for r in reviews if r.decision == Status.accepted)
#     rejected = sum(1 for r in reviews if r.decision == Status.rejected)
#     pending = sum(1 for r in reviews if r.decision is None)

#     # Per-project stats
#     project_stats = {}
#     # number assigned per project
#     for alloc in allocations:
#         submission = alloc.submission
#         project = submission.assignment.project if submission and submission.assignment else None
#         if not project:
#             continue
#         key = project.id
#         if key not in project_stats:
#             project_stats[key] = {
#                 "project_id": project.id,
#                 "project_name": project.name,
#                 "number_assigned": 0,
#                 "total_reviewed": 0,
#                 "approved": 0,
#                 "rejected": 0,
#                 "pending": 0,
#             }
#         project_stats[key]["number_assigned"] += 1

#     # add completed reviews per project
#     for review in reviews:
#         submission = review.submission
#         project = submission.assignment.project if submission and submission.assignment else None
#         if not project:
#             continue
#         key = project.id
#         if key not in project_stats:
#             project_stats[key] = {
#                 "project_id": project.id,
#                 "project_name": project.name,
#                 "number_assigned": 0,
#                 "total_reviewed": 0,
#                 "approved": 0,
#                 "rejected": 0,
#                 "pending": 0,
#             }
#         project_stats[key]["total_reviewed"] += 1
#         if review.decision == Status.accepted:
#             project_stats[key]["approved"] += 1
#         elif review.decision == Status.rejected:
#             project_stats[key]["rejected"] += 1
#         else:
#             project_stats[key]["pending"] += 1

#     return {
#         "reviewer_email": email,
#         "total_reviewed": total_reviewed,
#         "approved_reviews": approved,
#         "rejected_reviews": rejected,
#         "pending_reviews": pending,
#         "per_project": list(project_stats.values()),
#     }



# ------------------- REVIEWER STATS -------------------




# ------------------- PLATFORM STATS -------------------
async def get_platform_stats(session: AsyncSession):
    """Overall platform stats."""

    total_users = (await session.execute(select(func.count()).select_from(User))).scalar()
    total_projects = (await session.execute(select(func.count()).select_from(Project))).scalar()
    total_allocations = (await session.execute(select(func.count()).select_from(ProjectAllocation))).scalar()

    submissions_result = await session.execute(select(Submission))
    submissions: List[Submission] = submissions_result.scalars().all()
    total_subs = len(submissions)
    approved = sum(1 for s in submissions if s.status == Status.accepted)
    rejected = sum(1 for s in submissions if s.status == Status.rejected)
    pending = sum(1 for s in submissions if s.status == Status.submitted)

    coins_result = await session.execute(select(CoinPayment))
    coin_payments: List[CoinPayment] = coins_result.scalars().all()
    total_coins = sum(c.coins_earned for c in coin_payments)

    return {
        "total_users": total_users,
        "total_projects": total_projects,
        "total_allocations": total_allocations,
        "total_submissions": total_subs,
        "approved_submissions": approved,
        "rejected_submissions": rejected,
        "pending_review_submissions": pending,
        "total_coins_paid": total_coins,
    }

# ------------------- DAILY STATS -------------------
async def get_daily_stats(session: AsyncSession, days: int = 7):
    """Stats per day (last N days)."""

    today = datetime.utcnow().date()
    daily_data = []

    for i in range(days):
        day = today - timedelta(days=i)
        start_of_day = datetime(day.year, day.month, day.day)
        end_of_day = start_of_day + timedelta(days=1)

        subs_result = await session.execute(
            select(Submission).where(
                Submission.created_at >= start_of_day,
                Submission.created_at < end_of_day
            )
        )
        subs: List[Submission] = subs_result.scalars().all()

        daily_data.append({
            "date": str(day),
            "audio_submissions": sum(1 for s in subs if s.type == TaskType.audio),
            "text_submissions": sum(1 for s in subs if s.type == TaskType.text),
            "image_submissions": sum(1 for s in subs if s.type == TaskType.image),
            "video_submissions": sum(1 for s in subs if s.type == TaskType.video),
            "total_submissions": len(subs),
        })

    return daily_data
