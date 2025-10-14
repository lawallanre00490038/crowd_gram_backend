from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from typing import Dict, Optional, List, Any
from fastapi import Form
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.utils.reviwer_auto_assignment import auto_assign_reviewer
from sqlmodel import select


from src.db.models import (
    Submission,
    ProjectAllocation,
    TaskType,
    Status,
    Task,
    User,
)
from src.db.database import get_session
from src.utils.s3 import upload_file_to_s3
from src.utils.text_helpers import get_effective_payload_text
from src.schemas.submission_schemas import SubmissionResponse, PromptInfo
from src.utils.file_to_s3 import fetch_and_upload_from_telegram


router = APIRouter()
ALLOWED_STATUSES = [
    Status.assigned, 
    Status.accepted, 
    Status.rejected, 
    Status.redo, 
    Status.submitted
]


# ---------------------------
# FILE UPLOAD
# ---------------------------
async def handle_file_upload(file: UploadFile, folder: str, allowed_types: Optional[list[str]] = None) -> str:
    """
    Uploads a file to S3.

    Args:
        file: UploadFile object
        folder: folder prefix in S3
        allowed_types: optional list of allowed MIME types

    Returns:
        str: uploaded file URL
    """
    if allowed_types and file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"File type {file.content_type} not allowed")

    content = await file.read()
    file_name = f"{folder}/{file.filename}"
    s3_path = await upload_file_to_s3(content, file_name, file.content_type)
    if not s3_path:
        raise HTTPException(status_code=500, detail=f"Failed to upload {folder} to S3")
    return s3_path



# ---------------------------
# CREATE SUBMISSION
# ---------------------------
@router.post("/projects/{project_id}/agent", response_model=SubmissionResponse)
async def create_submission(
    project_id: str,
    task_id: str = Form(...),
    assignment_id: str = Form(...),
    user_id: Optional[str] = Form(None),
    user_email: Optional[str] = Form(None),
    type: Optional[TaskType] = Form(None),
    payload_text: Optional[str] = Form(None),
    telegram_file_id: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    session: AsyncSession = Depends(get_session),
):
    """
    Create a submission for a task in a project (supports Telegram or direct upload).

    This endpoint allows a contributor (agent) to submit their response for a task they
    have been assigned to. The submission is linked to a ProjectAllocation (assignment_id),
    ensuring only the assigned user can submit, and only once per allocation.

    Supported submission types:
    - text  → requires `payload_text`
    - audio → requires either `telegram_file_id` or `file` (ogg, mp3, wav)
    - image → requires `file` (png, jpg)
    - video → requires `file` (mp4)

    Validation rules:
    1. assignment_id must exist and belong to the project.
    2. User must match the allocation (by id or email).
    3. Only one submission is allowed per allocation.
    4. Task type must be consistent with provided content.

    Parameters (multipart/form-data):
    - task_id: str (required) → Task being submitted.
    - assignment_id: str (required) → Allocation ID from ProjectAllocation.
    - user_id: str (optional) → Contributor ID, validated against allocation.
    - user_email: str (optional) → Contributor email, validated against allocation.
    - type: TaskType (optional) → One of text, audio, image, video.
    - payload_text: str (optional) → Text submission content.
    - telegram_file_id: str (optional) → Telegram Bot API file_id for audio/image/video.
    - file: UploadFile (optional) → Direct file upload.

    Response:
    - Returns the created Submission object including submission id, task_id,
    assignment_id, user_id/email, type, payload_text, file_url, status, and timestamps.

    Errors:
    - 400 Bad Request → Invalid type, missing required fields, or duplicate submission.
    - 403 Forbidden   → User does not match allocation.
    - 404 Not Found   → Allocation not found for this project.
    """
    # --- Validate allocation --- also get the task prompt
    result = await session.execute(
        select(ProjectAllocation)
        .where(
            ProjectAllocation.id == assignment_id,
            ProjectAllocation.project_id == project_id
        )
        .options(
            selectinload(ProjectAllocation.submission),
            selectinload(ProjectAllocation.project)
        )
    )
    db_task_alloc = result.scalars().first()
    print(f"db_task_alloc: {db_task_alloc}\n\n\n\n")
    if not db_task_alloc:
        raise HTTPException(status_code=404, detail="Allocation not found for this project")

    # Validate user
    if user_id and db_task_alloc.user_id != user_id:
        raise HTTPException(status_code=403, detail="User ID mismatch with allocation")
    if user_email and db_task_alloc.user_email != user_email:
        raise HTTPException(status_code=403, detail="User email mismatch with allocation")


    existing_submission = db_task_alloc.submission
    if existing_submission and existing_submission.status != Status.redo:
        raise HTTPException(status_code=400, detail="Submission already exists for this task")


    # --- Handle file uploads ---
    file_url = None
    if type == TaskType.text:
        if not payload_text:
            raise HTTPException(status_code=400, detail="Text submission requires payload_text")
    elif type == TaskType.audio:
        if telegram_file_id:
            file_url = await fetch_and_upload_from_telegram(telegram_file_id, "audio")
        elif file:
            file_url = await handle_file_upload(file, "audio", ["audio/mpeg", "audio/ogg", "audio/wav"])
        else:
            raise HTTPException(status_code=400, detail="Audio submission requires file or telegram_file_id")
    elif type == TaskType.image:
        if not file:
            raise HTTPException(status_code=400, detail="Image submission requires file")
        file_url = await handle_file_upload(file, "image", ["image/png", "image/jpeg"])
    elif type == TaskType.video:
        if not file:
            raise HTTPException(status_code=400, detail="Video submission requires file")
        file_url = await handle_file_upload(file, "video", ["video/mp4"])
    else:
        raise HTTPException(status_code=400, detail="Task type must be specified")


    # --- Create submission ---
    submission = Submission(
        task_id=task_id,
        assignment_id=assignment_id,
        user_id=db_task_alloc.user_id,
        type=type,
        file_url=file_url,
        payload_text=payload_text,
        status=Status.submitted,
    )
    session.add(submission)

    # Update allocation
    db_task_alloc.submission = submission
    db_task_alloc.status = Status.submitted
    db_task_alloc.submitted_at = datetime.utcnow()
    session.add(db_task_alloc)
    
    # --- Track Project-level redo count ---
    if existing_submission and existing_submission.status == Status.redo:
        if db_task_alloc.project:
            db_task_alloc.project.num_redo = (db_task_alloc.project.num_redo or 0) + 1
            session.add(db_task_alloc.project)


    await session.commit()
    await session.refresh(submission)

    # --- Construct SubmissionResponse ---
    project_id_resp = db_task_alloc.project.id if db_task_alloc.project else None
    result_auto_assign = await auto_assign_reviewer(
        project_id=project_id,
        submission=submission,
        session=session
    )
    print(f"result_auto_assign: {result_auto_assign}\n\n\n\n")

    return SubmissionResponse(
        submission_id=submission.id,
        project_id=project_id_resp,
        task_id=submission.task_id,
        assignment_id=submission.assignment_id,
        user_id=submission.user_id,
        type=submission.type,
        num_redo=db_task_alloc.project.num_redo if db_task_alloc.project else None,
        payload_text=submission.payload_text,
        file_url=submission.file_url,
        status=submission.status,
        created_at=submission.created_at,
        updated_at=submission.updated_at,
    )


# ---------------------------
# LIST SUBMISSIONS (ALL)
# ---------------------------
@router.get("/all/agent", response_model=List[SubmissionResponse])
async def list_submissions(
    project_id: Optional[str] = None,
    user_id: Optional[str] = None,
    user_email: Optional[str] = None,
    status: Optional[List[Status]] = Query([Status.submitted], description="Filter by status(es)"),
    session: AsyncSession = Depends(get_session),
):
    """
    Retrieve submissions with optional filters:
    - project_id (all tasks under a project)
    - user_id (all submissions by a contributor)
    - user_email (all submissions by a contributor via email)
    - status (submitted, approved, rejected, etc.)

    Returns:
        List[SubmissionResponse]: Submission records with contributor and project info.
    """

    # ✅ Validate allowed statuses
    for s in status:
        if s not in ALLOWED_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Status must be one of: {[s.value for s in ALLOWED_STATUSES]}",
            )

    # ✅ Build query with eager loading
    query = (
        select(Submission)
        .options(
            selectinload(Submission.assignment).selectinload(ProjectAllocation.project),
            selectinload(Submission.task).selectinload(Task.prompt),
            selectinload(Submission.user),
        )
    )

    # ✅ Filter by project
    if project_id:
        query = query.join(Submission.assignment).where(ProjectAllocation.project_id == project_id)

    # ✅ Filter by contributor (ID or email)
    if user_id:
        query = query.where(Submission.user_id == user_id)
    elif user_email:
        query = query.join(Submission.user).where(User.email == user_email)

    # ✅ Fix status filtering (use IN instead of ==)
    if status:
        query = query.where(Submission.status.in_(status))

    # ✅ Execute
    result = await session.execute(query)
    submissions = result.scalars().unique().all()  # unique() prevents duplicates from joins

    # ✅ Construct response list
    submission_list = []
    for s in submissions:
        prompt_obj = s.task.prompt if s.task and s.task.prompt else None
        payload_text = get_effective_payload_text(s, s.task.prompt)
        if isinstance(payload_text, tuple) and len(payload_text) == 1:
            payload_text = payload_text[0]

        project_id_resp = (
            s.assignment.project_id if s.assignment else s.task.project_id if s.task else None
        )

        submission_list.append(
            SubmissionResponse(
                submission_id=s.id,
                project_id=project_id_resp,
                task_id=s.task_id,
                assignment_id=s.assignment_id,
                user_id=s.user.id if s.user else None,
                user_email=s.user.email if s.user else None,
                type=s.type,
                payload_text=payload_text,
                file_url=s.file_url,
                status=s.status,
                created_at=s.created_at,
                updated_at=s.updated_at,
                prompt=PromptInfo(
                    prompt_id=prompt_obj.id if prompt_obj else None,
                    sentence_id=prompt_obj.id if prompt_obj else None,
                    sentence_text=prompt_obj.text if prompt_obj else None,
                    media_url=prompt_obj.media_url if prompt_obj else None,
                    category=prompt_obj.category if prompt_obj else None,
                    domain=prompt_obj.domain if prompt_obj else None,
                )
                if prompt_obj
                else None,
            )
        )

    return submission_list




# ---------------------------
# GET SUBMISSION BY ID
# ---------------------------
@router.get("/{submission_id}/agent", response_model=SubmissionResponse)
async def get_submission(
    submission_id: str,
    session: AsyncSession = Depends(get_session)
):  
    """
    Fetch a submission by its ID.

    Args:
        submission_id (str): Unique ID of the submission to retrieve.
        session (Session): Database session dependency.

    Returns:
        Submission: Submission record including linked assignment and task.

    Raises:
        HTTPException: 404 if the submission does not exist.

    Notes:
        - Useful for displaying submission details to users, reviewers, or admins.
    """
    result = await session.execute(
        select(Submission)
        .where(Submission.id == submission_id)
        .options(
            selectinload(Submission.task)
            .selectinload(Task.prompt),        # load prompt under task
            selectinload(Submission.assignment),
            selectinload(Submission.user)
        )
    )
    submission = result.scalars().first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    project_id = submission.assignment.project_id if submission.assignment else submission.task.project_id if submission.task else None

    payload_text=get_effective_payload_text(submission, submission.task.prompt),
    if isinstance(payload_text, tuple) and len(payload_text) == 1:
        payload_text = payload_text[0]

    prompt_obj = submission.task.prompt if submission.task and submission.task.prompt else None

    return SubmissionResponse(
        submission_id=submission.id,
        project_id=project_id,
        task_id=submission.task_id,
        assignment_id=submission.assignment_id,
        user_id=submission.user_id,
        user_email=submission.user.email if submission.user else None,
        type=submission.type,
        payload_text=payload_text,
        file_url=submission.file_url,
        status=submission.status,
        created_at=submission.created_at,
        updated_at=submission.updated_at,
        prompt=PromptInfo(
            prompt_id=prompt_obj.id if prompt_obj else None,
            sentence_id=prompt_obj.id if prompt_obj else None,
            sentence_text=prompt_obj.text if prompt_obj else None,
            media_url=prompt_obj.media_url if prompt_obj else None,
            category=prompt_obj.category if prompt_obj else None,
            domain=prompt_obj.domain if prompt_obj else None,
        ) if prompt_obj else None
    )
