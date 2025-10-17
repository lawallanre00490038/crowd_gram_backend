import random
from typing import Optional
from fastapi import HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select, func
from datetime import datetime

from src.db.models import (
    Project,
    Status,
    ReviewerAllocation,
    Submission,
    ProjectReviewer,
    Task
)



async def auto_assign_reviewer(
    project_id: str,
    submission: Submission,
    session: AsyncSession,
) -> Optional[str]:
    """
    Automatically assigns an available reviewer to a submission
    based on reviewer pool and workload capacity (per project).
    """

    # 1️⃣ Load project with its reviewers
    project_stmt = (
        select(Project)
        .options(
            selectinload(Project.project_reviewers)
            .selectinload(ProjectReviewer.reviewer)
        )
        .where(Project.id == project_id)
    )
    project_result = await session.execute(project_stmt)
    project = project_result.scalars().first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # 2️⃣ Extract active reviewers
    project_reviewers = [
        pr.reviewer for pr in project.project_reviewers if pr.active and pr.reviewer
    ]
    if not project_reviewers:
        raise HTTPException(status_code=400, detail="No active reviewers for this project")

    # 3️⃣ Count reviewer workloads (only within this project)
    load_stmt = (
        select(
            ReviewerAllocation.reviewer_id,
            func.count(ReviewerAllocation.id).label("load_count")
        )
        .join(Submission, Submission.id == ReviewerAllocation.submission_id)
        .join(Task, Task.id == Submission.task_id)
        .where(Task.project_id == project_id)
        .group_by(ReviewerAllocation.reviewer_id)
    )
    load_result = await session.execute(load_stmt)
    reviewer_loads = {row.reviewer_id: row.load_count for row in load_result}

    # 4️⃣ Filter reviewers below project quota
    available_reviewers = [
        reviewer for reviewer in project_reviewers
        if reviewer_loads.get(reviewer.id, 0) < project.reviewer_quota
    ]
    if not available_reviewers:
        raise HTTPException(
            status_code=400,
            detail="All reviewers have reached their maximum capacity for this project"
        )

    # 5️⃣ Pick the least-loaded reviewer (balanced)
    selected_reviewer = min(
        available_reviewers,
        key=lambda r: reviewer_loads.get(r.id, 0)
    )

    print(f"🔍 Assigning submission {submission.id} to reviewer {selected_reviewer.email}")

    # 6️⃣ Create reviewer allocation
    review_alloc = ReviewerAllocation(
        submission_id=submission.id,
        reviewer_id=selected_reviewer.id,
        status=Status.pending,
        assigned_at=datetime.utcnow()
    )
    session.add(review_alloc)
    await session.commit()

    print(f"✅ Submission {submission.id} assigned to {selected_reviewer.email}")
    return selected_reviewer.email


