import pandas as pd
from sqlmodel import Session, select
from fastapi import HTTPException, UploadFile
from src.db.models import User, Role
from src.utils.auth import get_password_hash
from sqlalchemy.ext.asyncio import AsyncSession

async def create_user_in_db(session: AsyncSession, user: User) -> User:
    """Reusable function to create and persist a user."""
    existing_result = await session.execute(select(User).where(User.email == user.email))
    existing = existing_result.scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    if user.password:
        user.password = get_password_hash(user.password)

    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user




async def process_excel_users(session: AsyncSession, file: UploadFile):
    """Read and create users from Excel file upload."""
    try:
        df = pd.read_excel(file.file, engine="openpyxl")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading Excel file: {e}")

    # ✅ Only name and email are required
    required = ["name", "email"]
    if not all(c in df.columns for c in required):
        raise HTTPException(status_code=400, detail=f"Required columns: {required}")

    created = 0
    created_users = []

    for _, row in df.iterrows():
        email = str(row["email"]).strip()
        existing_result = await session.execute(select(User).where(User.email == email))
        existing = existing_result.scalars().first()
        if existing:
            continue


        # Safely get and split comma-separated strings
        languages_str = str(row.get("language", "")).strip()
        languages_list = [lang.strip() for lang in languages_str.split(",") if lang.strip()] if languages_str else []

        dialects_str = str(row.get("dialect", "")).strip()
        dialects_list = [d.strip() for d in dialects_str.split(",") if d.strip()] if dialects_str else []

        # Password
        raw_password = row.get("password")
        print(f"Raw password: {raw_password}")
        password = str(raw_password).strip() if raw_password and pd.notna(raw_password) else None
        hashed_password = get_password_hash(password) if password else None
        

        role_str = row.get("role", "agent")
        try:
            role_enum = Role(role_str)
        except ValueError:
            role_enum = Role.agent

        user = User(
            name=str(row["name"]).strip(),
            email=email,
            role=role_enum,
            password=hashed_password,
            telegram_id=row.get("telegram_id", None),
            languages=languages_list,
            dialects=dialects_list,
        )
        session.add(user)
        await session.flush()
        created += 1
        created_users.append(user)

    await session.commit()
    
    print(f"Created {created} users")
    return {
        "count": created, 
        "users": created_users
    }
