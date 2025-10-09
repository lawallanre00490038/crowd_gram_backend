from datetime import datetime
from sqlmodel import Session, select
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
        return existing_payment  # Already paid, do nothing

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

    return None  # Not accepted → no payment


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
        assignment_id=submission.id,  # track per submission
        coins_earned=coin_amt,
        approved=True,
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment





# async def award_coins_on_accept(session: AsyncSession, submission: Submission):
#     """
#     Award or revoke coins to the contributor based on submission status.
#     """
#     # Find allocation
#     alloc_result = await session.execute(
#         select(ProjectAllocation)
#         .join(ProjectAllocation.submission)
#         .where(Submission.id == submission.id)
#     )
#     alloc = alloc_result.scalars().first()
#     if not alloc:
#         return

#     # Check existing payment
#     existing_result = await session.execute(
#         select(CoinPayment).where(
#             CoinPayment.assignment_id == alloc.id,
#             CoinPayment.user_id == submission.user_id
#         )
#     )
#     existing = existing_result.scalars().first()

#     if submission.status in (Status.accepted, Status.approved):
#         # Create payment if it doesn't exist
#         if not existing:
#             proj = await session.get(Project, alloc.project_id) if alloc.project_id else None
#             coin_amt = proj.agent_coin if proj else 0.0
#             coin = CoinPayment(
#                 user_id=submission.user_id,
#                 project_id=alloc.project_id,
#                 assignment_id=alloc.id,
#                 task_id=submission.task_id,
#                 coins_earned=coin_amt,
#                 approved=True,
#             )
#             session.add(coin)
#             await session.commit()
#             await session.refresh(coin)
#             return coin
#     else:
#         # Revoke coins if submission was previously approved
#         if existing:
#             await session.delete(existing)
#             await session.commit()
#             return None




# async def award_reviewer_payment(session: AsyncSession, reviewer_id: str, project_id: str):
#     """
#     Award coins to a reviewer once per project review.
#     """
#     # Check if reviewer has already been paid for this project
#     existing_result = await session.execute(
#         select(CoinPayment).where(
#             CoinPayment.user_id == reviewer_id,
#             CoinPayment.project_id == project_id,
#             CoinPayment.task_id.is_(None),
#         )
#     )
#     existing = existing_result.scalars().first()
#     if existing:
#         return existing

#     project = await session.get(Project, project_id)
#     if not project:
#         return None

#     coin_amt = project.reviewer_coin
#     payment = CoinPayment(
#         user_id=reviewer_id,
#         project_id=project_id,
#         coins_earned=coin_amt,
#         approved=True,
#     )
#     session.add(payment)
#     await session.commit()
#     await session.refresh(payment)
#     return payment
