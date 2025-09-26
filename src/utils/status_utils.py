from sqlmodel import select, Session
from sqlalchemy.orm import selectinload
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import ProjectAllocation, Status



async def get_allocations_by_status(
    user_id: str,
    session: AsyncSession,
    statuses: Optional[list["Status"]] = None,
):
    query = (
        select(ProjectAllocation)
        .options(selectinload(ProjectAllocation.project))
        .where(ProjectAllocation.user_id == user_id)
    )
    if statuses:
        query = query.where(ProjectAllocation.status.in_(statuses))

    result = await session.execute(query)
    # print("The result is: ", result.scalars().all(), "\n\n\n")
    return result.scalars().all()