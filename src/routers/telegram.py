from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from src.db.models import User, CoinPayment, Role, ProjectAllocation, Submission, Review, Status
from src.db.database import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from src.utils.auth import get_password_hash, verify_password
from src.schemas.user_schemas import UserRegisterRequest, UserResponse, UserStatusResponse
from sqlalchemy import func

router = APIRouter()


@router.post("/register", response_model=UserResponse)
async def register_telegram_user(payload: UserRegisterRequest, session: AsyncSession = Depends(get_session)):
    """Register or link a Telegram account to an existing user based on email."""
    user_result = await session.execute(select(User).where(User.email == payload.email))
    user = user_result.scalars().first()

    if user:
        # If telegram_id already linked to another, reject
        if user.telegram_id and payload.telegram_id and user.telegram_id != payload.telegram_id:
            raise HTTPException(
                status_code=400,
                detail="This email is already linked to another Telegram ID."
            )

        user.telegram_id = payload.telegram_id or user.telegram_id
        user.languages = payload.languages or user.languages
        user.dialects = payload.dialects or user.dialects

        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    user = User(
        name=payload.name,
        email=payload.email,
        password=get_password_hash(payload.password),
        role=payload.role,
        telegram_id=payload.telegram_id,
        languages=payload.languages,
        dialects=payload.dialects
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user




@router.get("/login")
async def login_telegram_user(email: str, password: Optional[str] = None, session: AsyncSession = Depends(get_session)):
    """Login a user with email (telegram_id is optional)."""
    user_result = await session.execute(select(User).where(User.email == email))
    user = user_result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found. Please register.")
    if password and not verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Incorrect password.")
    return {
        "message": "Login successful.", 
        "user_id": user.id, "telegram_id": user.telegram_id,
        "user_role": user.role, "user_languages": user.languages,
        "user_dialects": user.dialects
    }


# /me endpoint using email (telegram optional)
@router.get("/me", response_model=UserResponse)
async def get_telegram_user(email: str, session: AsyncSession = Depends(get_session)):
    """Fetch user's info by email (telegram optional)."""
    user_result = await session.execute(select(User).where(User.email == email))
    user = user_result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found. Please register.")
    return user



@router.get("/status/{email}", response_model=UserStatusResponse)
async def get_telegram_status(email: str, session: AsyncSession = Depends(get_session)):
    """Fetch user's status by email (telegram optional)."""
    user_result = await session.execute(select(User).where(User.email == email))
    user = user_result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found. Please register.")

    # Base info
    coins_earned_result = await session.execute(
        select(CoinPayment.coins_earned).where(CoinPayment.user_id == user.id)
    )
    coins_earned = coins_earned_result.scalars().first() or 0

    base_status = {
        "role": user.role,
        "languages": user.languages,
        "dialects": user.dialects,
        "coins_earned": coins_earned,
    }

    if user.role == Role.agent:
        assigned_tasks_result = await session.execute(
            select(ProjectAllocation).where(ProjectAllocation.user_id == user.id)
        )
        assigned_tasks = assigned_tasks_result.scalars().all()

        completed_tasks = [t for t in assigned_tasks if t.completed_at]
        pending_tasks = [t for t in assigned_tasks if not t.completed_at]

        # ✅ Count submissions directly in DB
        sentences_read_result = await session.execute(
            select(func.count()).select_from(Submission).where(Submission.user_id == user.id)
        )
        sentences_read = sentences_read_result.scalar_one()

        base_status.update({
            "total_tasks_assigned": len(assigned_tasks),
            "completed_tasks": len(completed_tasks),
            "pending_tasks": len(pending_tasks),
            "sentences_read": sentences_read,
        })

    elif user.role == Role.reviewer:
        tasks_assigned_to_review_result = await session.execute(
            select(func.count()).select_from(Review).where(Review.reviewer_id == user.id)
        )
        tasks_assigned_to_review = tasks_assigned_to_review_result.scalar_one()

        completed_reviews_result = await session.execute(
            select(func.count()).select_from(Review).where(
                Review.reviewer_id == user.id,
                Review.decision == Status.approved
            )
        )
        completed_reviews = completed_reviews_result.scalar_one()

        base_status.update({
            "tasks_assigned_to_review": tasks_assigned_to_review,
            "completed_reviews": completed_reviews,
        })

    return base_status
