from datetime import datetime
from sqlmodel import  select
from sqlalchemy.orm import selectinload

from fastapi import HTTPException
from src.db.models import Project, ProjectAllocation, CoinPayment, Status, Submission, ReviewerAllocation, Task
from sqlalchemy.ext.asyncio import AsyncSession


# async def award_coins_on_accept(session: AsyncSession, submission: Submission):
#     """

#         Award coins to the agent once per submission if accepted.
#         Redos do NOT trigger additional payments.
#     """
#     # Find the allocation
#     alloc_result = await session.execute(
#         select(ProjectAllocation)
#         .where(ProjectAllocation.id == submission.assignment_id)
#     )
#     alloc = alloc_result.scalars().first()
#     if not alloc:
#         return None

#     # Check if payment already exists
#     existing_result = await session.execute(
#         select(CoinPayment).where(
#             CoinPayment.assignment_id == alloc.id,
#             CoinPayment.user_id == submission.user_id
#         )
#     )
#     existing_payment = existing_result.scalars().first()
#     if existing_payment:
#         return existing_payment

#     # Only award if submission is accepted
#     if submission.status in (Status.accepted, Status.approved):
#         project = await session.get(Project, alloc.project_id) if alloc.project_id else None
#         coin_amt = project.agent_coin if project else 0.0

#         payment = CoinPayment(
#             user_id=submission.user_id,
#             project_id=alloc.project_id,
#             project_allocation_id=alloc.id,
#             task_id=submission.task_id,
#             coins_earned=coin_amt,
#             approved=True,
#         )
#         session.add(payment)
#         await session.commit()
#         await session.refresh(payment)
#         return payment
#     return None


async def award_coins_on_accept(session: AsyncSession, submission: Submission):
    """
    Award coins to the agent once per submission if accepted.
    Redos do NOT trigger additional payments.
    """
    # 1️⃣ Find the project allocation for this submission
    alloc_result = await session.execute(
        select(ProjectAllocation).where(ProjectAllocation.id == submission.assignment_id)
    )
    alloc = alloc_result.scalars().first()
    if not alloc:
        raise HTTPException(status_code=404, detail="Project allocation not found")

    # 2️⃣ Check if a payment already exists for this allocation + user
    existing_result = await session.execute(
        select(CoinPayment).where(
            CoinPayment.user_id == submission.user_id,
            CoinPayment.project_allocation_id == alloc.id
        )
    )
    existing_payment = existing_result.scalars().first()
    if existing_payment:
        return existing_payment  # Already paid, do nothing

    # 3️⃣ Only award if submission is accepted or approved
    if submission.status not in (Status.accepted, Status.approved):
        return None

    # 4️⃣ Fetch project and determine coin amount
    project = await session.get(Project, alloc.project_id) if alloc.project_id else None
    coin_amt = project.agent_coin if project else 0.0

    # 5️⃣ Create and persist coin payment
    payment = CoinPayment(
        user_id=submission.user_id,
        project_id=alloc.project_id,
        project_allocation_id=alloc.id,
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

    # 3️⃣ Fetch the submission and project
    submission = await session.get(Submission, submission_id)
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



# async def award_reviewer_payment(session: AsyncSession, reviewer_id: str, submission_id: str):
#     """
#     Award coins to a reviewer once per submission.
#     Payment is only made if the ReviewerAllocation status is accepted.
#     """
#     # Check if reviewer has already been paid for this submission
#     existing_result = await session.execute(
#         select(CoinPayment).where(
#             CoinPayment.user_id == reviewer_id,
#             CoinPayment.task_id == submission_id  # Assuming task_id or link to submission_id
#         )
#     )
#     existing_payment = existing_result.scalars().first()
#     if existing_payment:
#         return existing_payment  # Already paid, skip

#     # Fetch reviewer allocation for this submission
#     reviewer_alloc_result = await session.execute(
#         select(ReviewerAllocation)
#         .where(
#             ReviewerAllocation.submission_id == submission_id,
#             ReviewerAllocation.reviewer_id == reviewer_id
#         )
#         .options(
#             selectinload(ReviewerAllocation.submission)
#             .selectinload(Submission.task)
#             .selectinload(Task.project)
#         )
#     )
#     reviewer_alloc = reviewer_alloc_result.scalars().first()
#     if not reviewer_alloc:
#         raise HTTPException(status_code=400, detail="Reviewer allocation not found")

#     #Only award coins if ReviewerAllocation status == accepted
#     if reviewer_alloc.status != Status.accepted:
#         return None

#     # Resolve project
#     submission = reviewer_alloc.submission
#     project = submission.task.project if submission and submission.task else None
#     if not project:
#         return None

#     # Create payment record
#     payment = CoinPayment(
#         user_id=reviewer_id,
#         project_id=project.id,
#         reviewer_allocation_id=reviewer_alloc.id,
#         coins_earned=project.reviewer_coin,
#         approved=True,
#     )
#     session.add(payment)
#     await session.commit()
#     await session.refresh(payment)
#     return payment
