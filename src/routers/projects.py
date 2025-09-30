from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import  select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import Path

from src.db.database import get_session
from src.utils.build_task_details import build_task_details
from src.db.models import Project, ProjectAllocation, Task, Submission, ReviewerAllocation, CoinPayment, User, Role
from src.schemas.project_schemas import (
    ProjectCreate,
    ProjectUpdate,
    ReviewerInfo,
    GetProjectInfo,
    ReviewInfo,
    ProjectTasksResponse,
    TaskWithUser,
    ProjectTasksResponseRich,
    ProjectReviewerTasksResponse,
    ReviewerWithTasks,
)

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


@router.patch("/update/project/{project_id}", response_model=Project)
async def update_project(project_id: str, project_in: ProjectUpdate, session: AsyncSession = Depends(get_session)):
    """Update a project (partial update)."""
    proj = await session.get(Project, project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    data = project_in.dict(exclude_unset=True)
    for k, v in data.items():
        setattr(proj, k, v)

    session.add(proj)
    await session.commit()
    await session.refresh(proj)
    return proj





# @router.get("/{project_id}/tasks/agent", response_model=ProjectTasksResponse)
# async def list_project_tasks_assigned_to_agents(
#     project_id: str,
#     status: Optional[str] = Query(None, description="Filter by allocation status"),
#     user_email: Optional[str] = Query(None, description="Filter by user email"),
#     user_id: Optional[str] = Query(None, description="Filter by user ID"),
#     prompt_id: Optional[str] = Query(None, description="Filter by sentence ID"),
#     session: AsyncSession = Depends(get_session)
# ):
#     """List tasks in a project along with their allocations.
#     Allows filtering by allocation status, user email/ID, and prompt ID.
#     """
#     result = await session.execute(
#         select(Project)
#         .options(
#             selectinload(Project.tasks)
#             .selectinload(Task.prompt),
#             selectinload(Project.tasks)
#             .selectinload(Task.allocations)
#             .selectinload(ProjectAllocation.user)
#         )
#         .where(Project.id == project_id)
#     )
#     project = result.scalars().first()
#     if not project:
#         raise HTTPException(status_code=404, detail="Project not found")

#     task_list = []
#     for task in project.tasks:
#         for alloc in task.allocations:
#             # Apply filters
#             if status and alloc.status.value != status:
#                 continue
#             if user_email and (alloc.user.email if alloc.user else alloc.user_email) != user_email:
#                 continue
#             if user_id and alloc.user_id != user_id:
#                 continue
#             if prompt_id and task.prompt_id != prompt_id:
#                 continue

#             task_list.append(TaskWithUser(
#                 task_id=task.id,
#                 assignment_id=alloc.id,
#                 prompt_id=task.prompt_id,
#                 sentence_id=task.prompt.id if task.prompt else None,
#                 sentence_text=task.prompt.text if task.prompt else None,
#                 user_id=alloc.user_id,
#                 user_email=alloc.user.email if alloc.user else alloc.user_email,
#                 assigned_at=alloc.assigned_at,
#                 status=alloc.status.value
#             ))

#     return ProjectTasksResponse(
#         project_id=project.id,
#         project_name=project.name,
#         tasks=task_list
#     )



# @router.get("/{project_id}/tasks/reviewer", response_model=ProjectTasksResponse)
# async def list_project_tasks_assigned_to_reviewers(
#     project_id: str,
#     status: Optional[str] = Query(None),
#     reviewer_email: Optional[str] = Query(None),
#     reviewer_id: Optional[str] = Query(None),
#     prompt_id: Optional[str] = Query(None),
#     session: AsyncSession = Depends(get_session)
# ):
#     """List tasks in a project along with their reviewer allocations and reviews.
#     Allows filtering by allocation status, reviewer email/ID, and prompt ID.
#     """
#     result = await session.execute(
#         select(Project)
#         .options(
#             selectinload(Project.tasks)
#             .selectinload(Task.submissions)
#             .selectinload(Submission.review_allocations)
#             .selectinload(ReviewerAllocation.reviewer),
#             selectinload(Project.tasks)
#             .selectinload(Task.prompt),
#             selectinload(Project.tasks)
#             .selectinload(Task.submissions)
#             .selectinload(Submission.reviews)
#         )
#         .where(Project.id == project_id)
#     )
#     project = result.scalars().first()
#     if not project:
#         raise HTTPException(status_code=404, detail="Project not found")

#     task_list = []
#     for task in project.tasks:
#         for submission in task.submissions:
#             for rev_alloc in submission.review_allocations:
#                 if status and rev_alloc.status.value != status:
#                     continue
#                 if reviewer_email and (rev_alloc.reviewer.email if rev_alloc.reviewer else None) != reviewer_email:
#                     continue
#                 if reviewer_id and rev_alloc.reviewer_id != reviewer_id:
#                     continue
#                 if prompt_id and task.prompt_id != prompt_id:
#                     continue

#                 # Find review by this reviewer for this submission
#                 review = next((r for r in submission.reviews if r.reviewer_id == rev_alloc.reviewer_id), None)

#                 # Get coins/payment earned by reviewer for this submission (if any)
#                 payment_result = await session.execute(
#                     select(CoinPayment)
#                     .where(
#                         CoinPayment.user_id == rev_alloc.reviewer_id,
#                         CoinPayment.project_id == project.id,
#                         CoinPayment.task_id == task.id
#                     )
#                 )
#                 payment = payment_result.scalars().first()

#                 task_list.append(TaskWithUser(
#                     task_id=task.id,
#                     assignment_id=rev_alloc.id,
#                     prompt_id=task.prompt_id,
#                     sentence_id=task.prompt.id if task.prompt else None,
#                     sentence_text=task.prompt.text if task.prompt else None,
#                     user_id=rev_alloc.reviewer_id,
#                     user_email=rev_alloc.reviewer.email if rev_alloc.reviewer else None,
#                     assigned_at=rev_alloc.assigned_at,
#                     status=rev_alloc.status.value,
#                     review_scores=review.scores if review else None,
#                     review_total_score=review.total_score if review else None,
#                     review_decision=review.decision.value if review else None,
#                     review_comments=review.comments if review else None,
#                     total_coins_earned=payment.coins_earned if payment else 0
#                 ))

#     return ProjectTasksResponse(
#         project_id=project.id,
#         project_name=project.name,
#         tasks=task_list
#     )




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





@router.get("/{project_id}/tasks/detailed")
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
        # ------------------------------
        # SAME LOGIC AS YOUR REVIEWER ROUTE
        # ------------------------------
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

        result = await session.execute(query)
        project = result.scalars().first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        task_ids = [t.id for t in project.tasks]
        payment_result = await session.execute(
            select(CoinPayment).where(
                CoinPayment.project_id == project.id,
                CoinPayment.task_id.in_(task_ids),
            )
        )
        all_payments = payment_result.scalars().all()
        payment_lookup = {(p.user_id, p.task_id): p for p in all_payments}

        from collections import defaultdict
        reviewers_map = defaultdict(lambda: {"reviewer_email": None, "tasks": []})

        for task in project.tasks:
            if prompt_id and task.prompt_id != prompt_id:
                continue

            for submission in task.submissions:
                user_email_value = submission.user.email if submission.user else (
                    submission.assignment.user_email if submission.assignment else None
                )

                for rev_alloc in submission.review_allocations:
                    if rev_alloc.reviewer and rev_alloc.reviewer.email != email:
                        continue
                    if status and rev_alloc.status.value.lower() != status.lower():
                        continue

                    review = next(
                        (r for r in submission.reviews if r.reviewer_id == rev_alloc.reviewer_id),
                        None,
                    )
                    payment = payment_lookup.get((rev_alloc.reviewer_id, task.id))

                    task_details = await build_task_details(
                        is_reviewer=True,
                        task=task,
                        rev_alloc=rev_alloc,
                        submission=submission,
                        review=review,
                        payment=payment,
                        user_email=user_email_value,
                    )

                    reviewers_map[rev_alloc.reviewer_id]["reviewer_email"] = rev_alloc.reviewer.email
                    reviewers_map[rev_alloc.reviewer_id]["tasks"].append(task_details)

        reviewers_out = [
            ReviewerWithTasks(
                reviewer_id=rid,
                reviewer_email=data["reviewer_email"],
                tasks=data["tasks"],
            )
            for rid, data in reviewers_map.items()
        ]

        return ProjectReviewerTasksResponse(
            project_id=project.id,
            project_name=project.name,
            reviewers=reviewers_out,
        )

    else:
        raise HTTPException(status_code=400, detail="Unsupported role for this query")














# @router.get("/{project_id}/tasks/agent/detailed", response_model=ProjectTasksResponseRich)
# async def list_project_tasks_assigned_to_agents(
#     project_id: str,
#     status: Optional[str] = None,
#     user_email: Optional[str] = None,
#     user_id: Optional[str] = None,
#     prompt_id: Optional[str] = None,
#     session: AsyncSession = Depends(get_session)
# ):
#     result = await session.execute(
#         select(Project)
#         .options(
#             # --- Keep your existing loads ---
#             selectinload(Project.tasks).selectinload(Task.prompt),
#             selectinload(Project.tasks)
#                 .selectinload(Task.allocations)
#                 .selectinload(ProjectAllocation.user),
            
#             # --- Modify this section to add the new loads ---
#             selectinload(Project.tasks)
#                 .selectinload(Task.allocations)
#                 .selectinload(ProjectAllocation.submission)
#                 .options(
#                     # 1. ADD THIS: Eagerly load the 'reviews' for each submission
#                     selectinload(Submission.reviews),
                    
#                     # 2. ADD THIS: Eagerly load the 'reviewer' user for each review allocation
#                     selectinload(Submission.review_allocations)
#                         .selectinload(ReviewerAllocation.reviewer)
#                 )
#         )
#         .where(Project.id == project_id)
#     )
#     project = result.scalars().first()

#     if not project:
#         raise HTTPException(status_code=404, detail="Project not found")

#     tasks_out = []
#     for task in project.tasks:
#         if prompt_id and task.prompt_id != prompt_id:
#             continue

#         for alloc in task.allocations:
#             # ✅ Filters
#             if status and alloc.status.value != status:
#                 continue

#             # ✅ Use getattr to avoid triggering lazy-load
#             email_value = getattr(alloc.user, "email", None) or alloc.user_email
#             if user_email and email_value != user_email:
#                 continue
#             if user_id and alloc.user_id != user_id:
#                 continue

#             submission = alloc.submission

#             # ✅ Collect reviewer allocations (all reviewers, not just first pending)
#             review_info = ReviewInfo(reviewers=[])
#             if submission and submission.review_allocations:
#                 for rev_alloc in submission.review_allocations:
#                     reviewer = ReviewerInfo(
#                         reviewer_id=rev_alloc.reviewer_id,
#                         reviewer_email=getattr(rev_alloc.reviewer, "email", None),
#                         review_scores=None,
#                         review_total_score=None,
#                         review_decision=rev_alloc.status.value,
#                         review_comments=None,
#                         total_coins_earned=None
#                     )
#                     review_info.reviewers.append(reviewer)

#             # ✅ Build safe task details
#             tasks_out.append(await build_task_details(
#                 task,
#                 alloc=alloc,
#                 submission=submission,
#                 rev_alloc=None,
#                 review=review_info if review_info.reviewers else None,
#                 payment=None,
#                 user_email=email_value
#             ))

#     return ProjectTasksResponseRich(
#         project_id=project.id,
#         project_name=project.name,
#         tasks=tasks_out
#     )



# # -------------------------
# # Reviewer Tasks Endpoint
# # -------------------------
# from collections import defaultdict

# @router.get("/{project_id}/tasks/reviewer/detailed", response_model=ProjectReviewerTasksResponse)
# async def list_project_tasks_assigned_to_reviewers(
#     project_id: str,
#     status: Optional[str] = None,
#     reviewer_email: Optional[str] = None,
#     reviewer_id: Optional[str] = None,
#     prompt_id: Optional[str] = None,
#     session: AsyncSession = Depends(get_session)
# ):
#     # --- Same query setup as before ---
#     query = (
#         select(Project)
#         .options(
#             selectinload(Project.tasks).selectinload(Task.prompt),
#             selectinload(Project.tasks).selectinload(Task.submissions).selectinload(Submission.user),
#             selectinload(Project.tasks).selectinload(Task.submissions).selectinload(Submission.assignment),
#             selectinload(Project.tasks).selectinload(Task.submissions)
#                 .selectinload(Submission.review_allocations)
#                 .selectinload(ReviewerAllocation.reviewer),
#             selectinload(Project.tasks).selectinload(Task.submissions).selectinload(Submission.reviews),
#         )
#         .where(Project.id == project_id)
#     )

#     if reviewer_email or reviewer_id:
#         query = (
#             query.join(Project.tasks)
#                  .join(Task.submissions)
#                  .join(Submission.review_allocations)
#                  .join(ReviewerAllocation.reviewer)
#         )
#         if reviewer_email:
#             query = query.where(User.email.ilike(reviewer_email))
#         if reviewer_id:
#             query = query.where(ReviewerAllocation.reviewer_id == reviewer_id)

#     result = await session.execute(query)
#     project = result.scalars().first()
#     if not project:
#         raise HTTPException(status_code=404, detail="Project not found")

#     # --- Prefetch payments ---
#     task_ids = [t.id for t in project.tasks]
#     payment_result = await session.execute(
#         select(CoinPayment).where(
#             CoinPayment.project_id == project.id,
#             CoinPayment.task_id.in_(task_ids)
#         )
#     )
#     all_payments = payment_result.scalars().all()
#     payment_lookup = {(p.user_id, p.task_id): p for p in all_payments}

#     # --- Group tasks by reviewer ---
#     reviewers_map = defaultdict(lambda: {"reviewer_email": None, "tasks": []})

#     for task in project.tasks:
#         if prompt_id and task.prompt_id != prompt_id:
#             continue

#         for submission in task.submissions:
#             user_email_value = submission.user.email if submission.user else (
#                 submission.assignment.user_email if submission.assignment else None
#             )

#             for rev_alloc in submission.review_allocations:
#                 if status and rev_alloc.status.value.lower() != status.lower():
#                     continue

#                 review = next((r for r in submission.reviews if r.reviewer_id == rev_alloc.reviewer_id), None)
#                 payment = payment_lookup.get((rev_alloc.reviewer_id, task.id))


#                 # Build task details
#                 task_details = await build_task_details(
#                     is_reviewer=True,
#                     task=task,
#                     rev_alloc=rev_alloc,
#                     submission=submission,
#                     review=review,
#                     payment=payment,
#                     user_email=user_email_value
#                 )

#                 # Insert into reviewer grouping
#                 reviewers_map[rev_alloc.reviewer_id]["reviewer_email"] = rev_alloc.reviewer.email
#                 reviewers_map[rev_alloc.reviewer_id]["tasks"].append(task_details)

#     # --- Transform into response ---
#     reviewers_out = [
#         ReviewerWithTasks(
#             reviewer_id=rid,
#             reviewer_email=data["reviewer_email"],
#             tasks=data["tasks"]
#         )
#         for rid, data in reviewers_map.items()
#     ]

#     return ProjectReviewerTasksResponse(
#         project_id=project.id,
#         project_name=project.name,
#         reviewers=reviewers_out
#     )
