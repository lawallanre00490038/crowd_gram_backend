from fastapi import HTTPException
from sqlmodel import Session, select
from src.db.models import Project, ProjectAllocation
from sqlalchemy.ext.asyncio import AsyncSession

async def validate_project_access(session: AsyncSession, project_id: str, user_id: str):
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.is_public:
        return project

    # private project: check allocation
    alloc = await session.execute(select(ProjectAllocation).where(
            ProjectAllocation.project_id == project_id,
            ProjectAllocation.user_id == user_id
        )
    ).first()

    if not alloc:
        raise HTTPException(status_code=403, detail="User not allocated to this project")

    return project
