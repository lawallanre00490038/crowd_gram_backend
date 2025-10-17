from datetime import datetime
from sqlmodel import  select
from src.db.models import Project, ProjectAllocation, CoinPayment, Status, Submission
from sqlalchemy.ext.asyncio import AsyncSession


async def award_coins_on_accept(session: AsyncSession, submission: Submission):
    """

        Award coins to the agent once per submission if accepted.
        Redos do NOT trigger additional payments.
    """
    # Find the allocation
    alloc_result = await session.execute(
        select(ProjectAllocation)
        .where(ProjectAllocation.id == submission.assignment_id)
    )
    alloc = alloc_result.scalars().first()
    if not alloc:
        return None

    # Check if payment already exists
    existing_result = await session.execute(
        select(CoinPayment).where(
            CoinPayment.assignment_id == alloc.id,
            CoinPayment.user_id == submission.user_id
        )
    )
    existing_payment = existing_result.scalars().first()
    if existing_payment:
        return existing_payment

    # Only award if submission is accepted
    if submission.status in (Status.accepted, Status.approved):
        project = await session.get(Project, alloc.project_id) if alloc.project_id else None
        coin_amt = project.agent_coin if project else 0.0

        payment = CoinPayment(
            user_id=submission.user_id,
            project_id=alloc.project_id,
            assignment_id=alloc.id,
            task_id=submission.task_id,
            coins_earned=coin_amt,
            approved=True,
        )
        session.add(payment)
        await session.commit()
        await session.refresh(payment)
        return payment
    return None





async def award_reviewer_payment(session: AsyncSession, reviewer_id: str, submission_id: str):
    """
    Award coins to a reviewer once per submission.
    If the reviewer has already been paid for this submission, do nothing.
    """
    # Check if reviewer has already been paid for this submission
    existing_result = await session.execute(
        select(CoinPayment).where(
            CoinPayment.user_id == reviewer_id,
            CoinPayment.assignment_id == submission_id
        )
    )
    existing_payment = existing_result.scalars().first()
    if existing_payment:
        return existing_payment  # Already paid, do nothing

    # Fetch the submission and project
    submission = await session.get(Submission, submission_id)
    if not submission:
        return None

    project = submission.task.project if submission.task else None
    if not project:
        return None

    coin_amt = project.reviewer_coin

    payment = CoinPayment(
        user_id=reviewer_id,
        project_id=project.id,
        assignment_id=submission.id,
        coins_earned=coin_amt,
        approved=True,
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment