from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import Session, select
from datetime import timedelta

from src.schemas.auth import Token, UserCreate, UserLogin
from src.db.models import User    
from src.db.database import get_session
from src.config import ACCESS_TOKEN_EXPIRE_MINUTES
from sqlalchemy.ext.asyncio import AsyncSession
from src.utils.auth import verify_password, get_password_hash, create_access_token, decode_access_token

router = APIRouter()


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@router.post("/signup", response_model=User)
async def register_user(*, user_create: UserCreate, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(User).where(User.email == user_create.email))
    existing_user = result.scalars().first()

    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(user_create.password)
    user = User(
        name=user_create.name,
        email=user_create.email,
        password=hashed_password,
        role=user_create.role,
        gender=user_create.gender,
        age_group=user_create.age_group,
        edu_level=user_create.edu_level,
        languages=user_create.languages,
        telegram_id=user_create.telegram_id
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@router.post("/signin", response_model=Token)
async def login_for_access_token(form_data: UserLogin, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(User).where(User.email == form_data.email))
    user = result.scalars().first()
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role}, expires_delta=access_token_expires
    )
    return {
        "message": "Login successful",
        "access_token": access_token, 
        "token_type": "bearer"
    }


async def get_current_user(token: str = Depends(oauth2_scheme), session: AsyncSession = Depends(get_session)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    email: str = payload.get("sub")
    if email is None:
        raise credentials_exception
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_admin_user(current_user: User = Depends(get_current_active_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user


async def get_current_reviewer_user(current_user: User = Depends(get_current_active_user)):
    if current_user.role not in ["reviewer", "super_reviewer", "admin"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user


async def get_current_contributor_user(current_user: User = Depends(get_current_active_user)):
    if current_user.role not in ["contributor", "admin"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user


