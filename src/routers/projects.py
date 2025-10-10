from typing import List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import  select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import Path
from collections import defaultdict

from src.db.database import get_session
from src.utils.build_task_details import build_task_details
from src.db.models import Project, ProjectAllocation, Task, Submission, ReviewerAllocation, CoinPayment, User, Role
from src.schemas.project_schemas import (
    ProjectCreate,
    ProjectUpdate,
    ReviewerInfo,
    GetProjectInfo,
    ReviewInfo,
    ProjectTasksResponseRich,
    ProjectReviewerTasksResponse,
    ReviewerWithTasks,
)
from src.schemas.project_general import ProjectTasksGeneralResponse

router = APIRouter()


@router.post("/create/project", response_model=Project)
async def create_project(project_in: ProjectCreate, session: AsyncSession = Depends(get_session)):
    """Create a new project."""
    # Check for duplicate project name
    result = await session.execute(select(Project).where(Project.name == project_in.name))
    existing_project = result.scalars().first()
    if existing_project:
        raise HTTPException(status_code=400, detail="Project name already exists")

    project = Project(**project_in.model_dump())
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project



@router.get("/list/projects", response_model=List[Project])
async def list_projects(session: AsyncSession = Depends(get_session)):
    """List all projects."""
    result = await session.execute(select(Project))
    projects = result.scalars().all()
    return projects


# Get a project by name or id
@router.post("/get/project", response_model=Project)
async def get_project(project_info: GetProjectInfo, session: AsyncSession = Depends(get_session)):
    """Get a project by name or id."""
    result = await session.execute(select(Project).where(Project.id == project_info.id))
    project = result.scalars().first()
    if not project:
        result = await session.execute(select(Project).where(Project.name == project_info.name))
        project = result.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/project/{project_id}/review-parameters", response_model=List[str])
async def get_review_parameters(
    project_id: str = Path(..., description="The ID of the project"),
    session: AsyncSession = Depends(get_session),
):
    """
    Get the review parameters of a project using its ID.
    """
    result = await session.execute(
        select(Project.review_parameters).where(Project.id == project_id)
    )
    review_params = result.scalars().first()

    if review_params is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return review_params



@router.get("/project/{project_id}/instructions", response_model=str | None)
async def get_project_instructions(
    project_id: str = Path(..., description="The ID of the project"),
    role: Role = Query(..., description="The role of the user"),
    session: AsyncSession = Depends(get_session),
):
    """
    Get project instructions based on the user's role.
    """
    result = await session.execute(
        select(
            Project.agent_instructions,
            Project.reviewer_instructions,
            Project.super_reviewer_instructions
        ).where(Project.id == project_id)
    )
    instructions = result.first()

    if not instructions:
        raise HTTPException(status_code=404, detail="Project not found")

    # ✅ Role-based mapping
    if role == Role.agent:
        return instructions[0]
    elif role == Role.reviewer:
        return instructions[1]
    elif role == Role.super_reviewer:
        return instructions[2]
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported role: {role}")




@router.patch("/update/project/{project_id}", response_model=Project)
async def update_project(project_id: str, project_in: ProjectUpdate, session: AsyncSession = Depends(get_session)):
    """Update a project (partial update)."""
    proj = await session.get(Project, project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        data = project_in.dict(exclude_unset=True)
        for k, v in data.items():
            setattr(proj, k, v)

        session.add(proj)
        await session.commit()
        await session.refresh(proj)
        return proj
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))




@router.get("/projects/by-email/{email}", response_model=List[Project])
async def get_projects_by_email(
    email: str,
    session: AsyncSession = Depends(get_session)
):
    """
    List all projects where a user (agent or reviewer) with the given email is involved.
    Role is determined from the User record.
    """
    # 1. Find user
    user_result = await session.execute(select(User).where(User.email == email))
    user = user_result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    projects = []
    
    # 2. Fetch projects based on role
    if user.role == Role.agent:
        result = await session.execute(
            select(Project)
            .join(Project.tasks)
            .join(Task.allocations)
            .join(ProjectAllocation.user)
            .where(User.email == email)
            .options(selectinload(Project.tasks))
        )
        projects = result.scalars().unique().all()

    elif user.role == Role.reviewer:
        result = await session.execute(
            select(Project)
            .join(Project.tasks)
            .join(Task.submissions)
            .join(Submission.review_allocations)
            .join(ReviewerAllocation.reviewer)
            .where(User.email == email)
            .options(selectinload(Project.tasks))
        )
        projects = result.scalars().unique().all()

    else:
        raise HTTPException(status_code=400, detail="Unsupported role for this query")

    if not projects:
        raise HTTPException(status_code=404, detail=f"No projects found for {user.role} with this email")

    return projects




@router.get("/{project_id}/tasks/detailed", response_model=Union[ProjectTasksResponseRich, ProjectReviewerTasksResponse])
async def list_project_tasks_by_role(
    project_id: str,
    email: str = Query(..., description="User email"),
    status: Optional[str] = Query(None),
    prompt_id: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
):
    """
    Fetch detailed project tasks for a user (agent or reviewer) based on their role.
    - If the user is an agent → returns ProjectTasksResponseRich
    - If the user is a reviewer → returns ProjectReviewerTasksResponse
    """
    # 1. Find user and determine role
    user_result = await session.execute(select(User).where(User.email == email))
    user = user_result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 2. Branch depending on role
    if user.role == Role.agent:
        # ------------------------------
        # SAME LOGIC AS YOUR AGENT ROUTE
        # ------------------------------
        result = await session.execute(
            select(Project)
            .options(
                selectinload(Project.tasks).selectinload(Task.prompt),
                selectinload(Project.tasks)
                    .selectinload(Task.allocations)
                    .selectinload(ProjectAllocation.user),
                selectinload(Project.tasks)
                    .selectinload(Task.allocations)
                    .selectinload(ProjectAllocation.submission)
                    .options(
                        selectinload(Submission.reviews),
                        selectinload(Submission.review_allocations)
                            .selectinload(ReviewerAllocation.reviewer),
                    ),
            )
            .where(Project.id == project_id)
        )
        project = result.scalars().first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        tasks_out = []
        for task in project.tasks:
            if prompt_id and task.prompt_id != prompt_id:
                continue

            for alloc in task.allocations:
                if alloc.user and alloc.user.email != email:
                    continue
                if status and alloc.status.value != status:
                    continue

                submission = alloc.submission

                review_info = ReviewInfo(reviewers=[])
                if submission and submission.review_allocations:
                    for rev_alloc in submission.review_allocations:
                        review_info.reviewers.append(
                            ReviewerInfo(
                                reviewer_id=rev_alloc.reviewer_id,
                                reviewer_email=getattr(rev_alloc.reviewer, "email", None),
                                review_scores=None,
                                review_total_score=None,
                                review_decision=rev_alloc.status.value,
                                review_comments=None,
                                total_coins_earned=None,
                            )
                        )

                tasks_out.append(
                    await build_task_details(
                        task,
                        alloc=alloc,
                        submission=submission,
                        rev_alloc=None,
                        review=review_info if review_info.reviewers else None,
                        payment=None,
                        user_email=email,
                    )
                )

        return ProjectTasksResponseRich(
            project_id=project.id,
            project_name=project.name,
            tasks=tasks_out,
        )

    elif user.role == Role.reviewer:
        
        query = (
            select(Project)
            .options(
                selectinload(Project.tasks).selectinload(Task.prompt),
                selectinload(Project.tasks).selectinload(Task.submissions).selectinload(Submission.user),
                selectinload(Project.tasks).selectinload(Task.submissions).selectinload(Submission.assignment),
                selectinload(Project.tasks).selectinload(Task.submissions)
                    .selectinload(Submission.review_allocations)
                    .selectinload(ReviewerAllocation.reviewer),
                selectinload(Project.tasks).selectinload(Task.submissions).selectinload(Submission.reviews),
            )
            .where(Project.id == project_id)
        )

        if email:
            query = (
                query.join(Project.tasks)
                    .join(Task.submissions)
                    .join(Submission.review_allocations)
                    .join(ReviewerAllocation.reviewer)
            )
            if email:
                query = query.where(User.email.ilike(email))

        result = await session.execute(query)
        project = result.scalars().first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # --- Prefetch payments ---
        task_ids = [t.id for t in project.tasks]
        payment_result = await session.execute(
            select(CoinPayment).where(
                CoinPayment.project_id == project.id,
                CoinPayment.task_id.in_(task_ids)
            )
        )
        all_payments = payment_result.scalars().all()
        payment_lookup = {(p.user_id, p.task_id): p for p in all_payments}

        # --- Group tasks by reviewer ---
        reviewers_map = defaultdict(lambda: {"reviewer_email": None, "tasks": []})

        for task in project.tasks:
            if prompt_id and task.prompt_id != prompt_id:
                continue

            for submission in task.submissions:
                user_email_value = submission.user.email if submission.user else (
                    submission.assignment.user_email if submission.assignment else None
                )

                for rev_alloc in submission.review_allocations:
                    if status and rev_alloc.status.value.lower() != status.lower():
                        continue

                    review = next((r for r in submission.reviews if r.reviewer_id == rev_alloc.reviewer_id), None)
                    payment = payment_lookup.get((rev_alloc.reviewer_id, task.id))


                    # Build task details
                    task_details = await build_task_details(
                        is_reviewer=True,
                        task=task,
                        rev_alloc=rev_alloc,
                        submission=submission,
                        review=review,
                        payment=payment,
                        user_email=user_email_value
                    )

                    # Insert into reviewer grouping
                    reviewers_map[rev_alloc.reviewer_id]["reviewer_email"] = rev_alloc.reviewer.email
                    reviewers_map[rev_alloc.reviewer_id]["tasks"].append(task_details)

        # --- Transform into response ---
        reviewers_out = [
            ReviewerWithTasks(
                reviewer_id=rid,
                reviewer_email=data["reviewer_email"],
                tasks=data["tasks"]
            )
            for rid, data in reviewers_map.items()
        ]

        return ProjectReviewerTasksResponse(
            project_id=project.id,
            project_name=project.name,
            reviewers=reviewers_out
        )




@router.get("/{project_id}/tasks/detailed/all", response_model=ProjectTasksGeneralResponse)
async def list_project_tasks_general(
    project_id: str,
    email: Optional[str] = Query(None, description="Filter by user email"),
    role: Optional[Role] = Query(None, description="Filter by role: agent or reviewer"),
    status: Optional[str] = Query(None, description="Filter by task/submission status"),
    prompt_id: Optional[str] = Query(None, description="Filter by prompt id"),
    limit: int = Query(50, ge=1, le=200, description="Max tasks per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    session: AsyncSession = Depends(get_session),
):
    """
    Fetch detailed project tasks with flexible filtering + pagination.
    - If no email is provided → return ALL tasks in the project.
    - If role=agent → return only agent allocations.
    - If role=reviewer → return only reviewer allocations.
    - If email is provided → filter tasks linked to that email.
    - Supports pagination with `limit` and `offset`.
    """
    # 1. Load the project with tasks
    result = await session.execute(
        select(Project)
        .options(
            selectinload(Project.tasks).selectinload(Task.prompt),
            selectinload(Project.tasks).selectinload(Task.allocations).selectinload(ProjectAllocation.user),
            selectinload(Project.tasks).selectinload(Task.allocations).selectinload(ProjectAllocation.submission)
                .options(
                    selectinload(Submission.reviews),
                    selectinload(Submission.review_allocations).selectinload(ReviewerAllocation.reviewer),
                ),
            selectinload(Project.tasks).selectinload(Task.submissions).selectinload(Submission.user),
            selectinload(Project.tasks).selectinload(Task.submissions).selectinload(Submission.assignment),
        )
        .where(Project.id == project_id)
    )
    project = result.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    all_tasks_out = []

    # 2. Collect tasks (agents + reviewers)
    for task in project.tasks:
        if prompt_id and task.prompt_id != prompt_id:
            continue

        # --- AGENTS ---
        for alloc in task.allocations:
            if email and alloc.user and alloc.user.email != email:
                continue
            if role and role == Role.reviewer:
                continue
            if status and alloc.status.value.lower() != status.lower():
                continue

            submission = alloc.submission
            review_info = ReviewInfo(reviewers=[])
            if submission and submission.review_allocations:
                for rev_alloc in submission.review_allocations:
                    review_info.reviewers.append(
                        ReviewerInfo(
                            reviewer_id=rev_alloc.reviewer_id,
                            reviewer_email=getattr(rev_alloc.reviewer, "email", None),
                            review_scores=None,
                            review_total_score=None,
                            review_decision=rev_alloc.status.value,
                            review_comments=None,
                            total_coins_earned=None,
                        )
                    )

            all_tasks_out.append(
                await build_task_details(
                    task,
                    alloc=alloc,
                    submission=submission,
                    rev_alloc=None,
                    review=review_info if review_info.reviewers else None,
                    payment=None,
                    user_email=alloc.user.email if alloc.user else None,
                )
            )

        # --- REVIEWERS ---
        for submission in task.submissions:
            user_email_value = (
                submission.user.email if submission.user else (
                    submission.assignment.user_email if submission.assignment else None
                )
            )

            for rev_alloc in submission.review_allocations:
                if email and rev_alloc.reviewer and rev_alloc.reviewer.email != email:
                    continue
                if role and role == Role.agent:
                    continue
                if status and rev_alloc.status.value.lower() != status.lower():
                    continue

                review = next(
                    (r for r in submission.reviews if r.reviewer_id == rev_alloc.reviewer_id),
                    None,
                )

                all_tasks_out.append(
                    await build_task_details(
                        is_reviewer=True,
                        task=task,
                        rev_alloc=rev_alloc,
                        submission=submission,
                        review=review,
                        payment=None,  # add payment lookup if needed
                        user_email=user_email_value,
                    )
                )

    # 3. Apply pagination
    total_count = len(all_tasks_out)
    paginated_tasks = all_tasks_out[offset: offset + limit]

    # 4. Response
    return {
        "project_id": project.id,
        "project_name": project.name,
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
        "returned_count": len(paginated_tasks),
        "tasks": paginated_tasks,
    }
