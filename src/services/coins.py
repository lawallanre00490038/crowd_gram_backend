from datetime import datetime
from sqlmodel import  select
from sqlalchemy.orm import selectinload

from fastapi import HTTPException
from src.db.models import Project, AgentAllocation, CoinPayment, Status, Submission, ReviewerAllocation, Task
from sqlalchemy.ext.asyncio import AsyncSession


# -------------------------------------------------------------------
# 🪙 AWARD AGENT COINS
# -------------------------------------------------------------------
async def award_coins_on_accept(session: AsyncSession, submission: Submission):
    """
    Award coins to the agent once per submission if accepted.
    Redos do NOT trigger additional payments.
    """
    alloc_result = await session.execute(
        select(AgentAllocation).where(AgentAllocation.id == submission.assignment_id)
    )
    alloc = alloc_result.scalars().first()
    if not alloc:
        raise HTTPException(status_code=404, detail="Project allocation not found")

    # Skip if already paid
    existing_result = await session.execute(
        select(CoinPayment).where(
            CoinPayment.user_id == submission.user_id,
            CoinPayment.agent_allocation_id == alloc.id
        )
    )
    if existing_result.scalars().first():
        return None

    if submission.status not in (Status.accepted, Status.approved):
        return None

    project_result = await session.execute(
        select(Project).where(Project.id == alloc.project_id)
    )
    project = project_result.scalars().first()
    coin_amt = project.agent_coin if project else 0.0

    payment = CoinPayment(
        user_id=submission.user_id,
        project_id=alloc.project_id,
        agent_allocation_id=alloc.id,
        task_id=submission.task_id,
        coins_earned=coin_amt,
        approved=True,
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment

    


async def award_reviewer_payment(session: AsyncSession, reviewer_id: str, submission_id: str):
    """
    Award coins to a reviewer once per submission.
    Coins are only awarded if the reviewer allocation status is 'accepted'.
    If the reviewer has already been paid for this submission, do nothing.
    """
    # 1️⃣ Fetch the ReviewerAllocation first
    reviewer_alloc_result = await session.execute(
        select(ReviewerAllocation).where(
            ReviewerAllocation.submission_id == submission_id,
            ReviewerAllocation.reviewer_id == reviewer_id
        )
    )
    reviewer_alloc = reviewer_alloc_result.scalars().first()

    if not reviewer_alloc:
        raise HTTPException(status_code=400, detail="Reviewer allocation not found")

    # nly award if reviewer allocation is accepted
    if reviewer_alloc.status != Status.accepted:
        return None

    # 2️⃣ Check if reviewer already paid for this allocation
    existing_result = await session.execute(
        select(CoinPayment).where(
            CoinPayment.user_id == reviewer_id,
            CoinPayment.reviewer_allocation_id == reviewer_alloc.id
        )
    )
    existing_payment = existing_result.scalars().first()
    if existing_payment:
        return existing_payment  # Already paid, do nothing

    # ✅ Preload submission with task + project
    submission_result = await session.execute(
        select(Submission)
        .options(selectinload(Submission.task).selectinload(Task.project))
        .where(Submission.id == submission_id)
    )
    submission = submission_result.scalars().first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    project = submission.task.project if submission.task else None
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # 4️⃣ Create payment
    coin_amt = project.reviewer_coin or 0.0

    payment = CoinPayment(
        user_id=reviewer_id,
        project_id=project.id,
        reviewer_allocation_id=reviewer_alloc.id,
        coins_earned=coin_amt,
        approved=True,
    )

    session.add(payment)
    await session.commit()
    await session.refresh(payment)

    return payment







