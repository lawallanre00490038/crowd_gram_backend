from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlmodel import Session, select
from typing import List, Optional, Dict, Any
from datetime import datetime
import pandas as pd
from src.db.models import Task, AgentAllocation, Prompt, Project, Status, User, TaskType
from src.db.database import get_session
from sqlalchemy.ext.asyncio import AsyncSession

from src.utils.read_file import read_uploaded_dataframe

router = APIRouter()


# ----------------------------
# Task CRUD
# ----------------------------
@router.get("/read/all", response_model=List[Task])
async def read_tasks(offset: int = 0, limit: int = 100, session: AsyncSession = Depends(get_session)):
    """
    Retrieve a paginated list of tasks.

    Args:
        offset (int): Number of tasks to skip (default 0).
        limit (int): Maximum number of tasks to return (default 100).
        session (Session): Database session dependency.

    Returns:
        List[Task]: List of Task objects.

    Notes:
        - Useful for admin dashboards or task management views.
        - Supports pagination to avoid large payloads.
    """
    result = await session.execute(select(Task).offset(offset).limit(limit))
    tasks = result.scalars().all()
    return tasks


@router.get("/{task_id}/read", response_model=Task)
async def read_task(task_id: str, session: AsyncSession = Depends(get_session)):
    """
    Retrieve a single Task by its unique ID.

    Args:
        task_id (str): ID of the Task to fetch.
        session (Session): Database session dependency.

    Returns:
        Task: Task object corresponding to the given ID.

    Raises:
        HTTPException: 404 if Task is not found.

    Notes:
        - Returns detailed information including prompt association and status.
    """
    task = await session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/{task_id}/update", response_model=Task)
async def update_task(task_id: str, task: Task, session: AsyncSession = Depends(get_session)):
    """
    Update an existing Task record.

    **Flow**:
    - Fetches the existing Task by ID.
    - Updates fields that are provided in the request.
    - Commits changes and returns updated Task.

    Args:
        task_id (str): ID of the Task to update.
        task (Task): Partial Task payload for updates.
        session (Session): Database session dependency.

    Returns:
        Task: Updated Task object.

    Raises:
        HTTPException: 404 if Task is not found.

    Notes:
        - Only fields provided in the payload are updated (others remain unchanged).
        - Use for updating status, type, or prompt association.
    """
    db_task = await session.get(Task, task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    task_data = task.model_dump(exclude_unset=True)
    db_task.sqlmodel_update(task_data)

    session.add(db_task)
    await session.commit()
    await session.refresh(db_task)
    return db_task
    


@router.delete("/{task_id}/delete")
async def delete_task(task_id: str, session: AsyncSession = Depends(get_session)):
    """
    Delete a Task by its ID.

    Args:
        task_id (str): ID of the Task to delete.
        session (Session): Database session dependency.

    Returns:
        Dict[str, bool]: Confirmation of deletion ({"ok": True}).

    Raises:
        HTTPException: 404 if Task is not found.

    Notes:
        - Deleting a Task will not automatically delete associated allocations or prompts.
        - Use with caution; ensure dependent records are handled separately.
    """
    task = await session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    session.delete(task)
    await session.commit()
    return {"ok": True}



@router.post("/{project_id}/allocate/read_task")
async def allocate_project_read_users(
    project_id: str,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    """
    Upload an Excel file to batch create and allocate audio tasks using **user email** for allocation.

    **Expected Excel Columns**:
    - sentence_id: Unique identifier for the sentence
    - sentence_text: Text content to convert to audio
    - user_email: Email of the user to assign the task to

    **Example Excel Data**:

    | sentence_id | sentence_text             | user_email           |
    |--------------|--------------------------|----------------------|
    | 1            | Hello world              | user1@example.com    |
    | 2            | Welcome to the platform  | user2@example.com    |
    | 3            | FastAPI makes life easy  | user3@example.com    |

    **Flow**:
    - Reads Excel file into a pandas DataFrame.
    - Validates that required columns exist.
    - Resolves `user_email` to `user_id`; raises error if email not found.
    - Creates new `Prompt` entries if needed.
    - Creates `Task` entries of type `'audio'`.
    - Allocates Tasks to users based on their email.
    - Returns summary of created and skipped tasks.
    """

    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    df = await read_uploaded_dataframe(file, {"sentence_id", "sentence_text", "user_email"})


    created_tasks = []
    skipped_rows = []

    for _, row in df.iterrows():
        try:
            sentence_id = str(row["sentence_id"])
            sentence_text = str(row["sentence_text"]).strip()
            user_email = str(row["user_email"]).strip()

            # Validate user
            user_result = await session.execute(select(User).where(User.email == user_email))
            user = user_result.scalars().first()
            if not user:
                skipped_rows.append({
                    "sentence_id": sentence_id,
                    "sentence_text": sentence_text,
                    "user_email": user_email,
                    "reason": "User email not found"
                })
                continue

            # Find or create prompt (no max_reuses logic)
            prompt_result = await session.execute(
                select(Prompt).where(
                    Prompt.text == sentence_text,
                    Prompt.project_id == project_id
                )
            )
            prompt = prompt_result.scalars().first()
            if not prompt:
                prompt = Prompt(
                    project_id=project_id,
                    id=sentence_id,
                    text=sentence_text,
                    domain="excel_upload",
                    category="speech",
                )
                session.add(prompt)
                await session.flush()

            # Create task
            task = Task(
                project_id=project_id,
                type=TaskType.audio,
                prompt_id=prompt.id,
                assigned_to=user.id,
                status=Status.pending,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(task)
            await session.flush()

            # Allocate task
            allocation = AgentAllocation(
                project_id=project_id,
                task_id=task.id,
                user_id=user.id,
                user_email=user.email,
                assigned_at=datetime.utcnow(),
                status=Status.assigned
            )
            session.add(allocation)

            created_tasks.append({
                "task_id": task.id,
                "sentence_id": sentence_id,
                "sentence_text": sentence_text,
                "user_email": user_email
            })

        except Exception as e:
            skipped_rows.append({"row_data": row.to_dict(), "reason": str(e)})

    await session.commit()

    return {
        "message": "Excel processed successfully",
        "created_tasks": created_tasks,
        "skipped_rows": skipped_rows,
        "summary": {
            "total_rows": len(df),
            "created": len(created_tasks),
            "skipped": len(skipped_rows),
            "project_name": project.name,
            "project_id": project.id,
        },
    }
