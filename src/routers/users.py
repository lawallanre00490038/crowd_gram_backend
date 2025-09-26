from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Body
from sqlmodel import Session, select
from typing import List, Optional
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import User
from src.db.database import get_session
from src.utils.user_utils import create_user_in_db, process_excel_users

router = APIRouter()

# ============================================================
# 🧩 USER CREATION
# ============================================================

@router.post("/create", response_model=User)
async def create_user(user: User, session: AsyncSession = Depends(get_session)):
    """
    📥 Create a single user manually.
    
    - **Required:** `name`, `email`
    - **Optional:** `password`, `role`, `languages`, `dialect`, `telegram_id`
    - If `password` is provided, it will be hashed before saving.
    """
    return await create_user_in_db(session, user)


# ============================================================
# 📊 BULK USER CREATION VIA EXCEL
# ============================================================

@router.post("/admin/create/bulk")
async def upload_users_excel(file: UploadFile = File(...), session: AsyncSession = Depends(get_session)):
    """
    📦 Bulk create users from an Excel file.

    **Expected columns:**
    - `name` (required)
    - `email` (required)
    - `password` (optional)
    - `role` (optional, defaults to `"agent"`)
    - `language` (optional, comma-separated list)
    - `dialect` (optional, comma-separated list)
    - `telegram_id` (optional)

    Example row:
    ```
    | name       | email              | password | role     | language           | dialect           | telegram_id |
    |------------|--------------------|----------|----------|--------------------|-------------------|--------------|
    | Jane Doe   | jane@example.com   | pass123  | agent    | English, Yoruba    | Ekiti, Ibadan     | @janedoe     |
    ```

    ✅ If a user already exists (by email), they are **skipped**.
    """
    created = await process_excel_users(session, file)
    return {"created": created}


# ============================================================
# 📜 USER LIST & DETAIL
# ============================================================

@router.get("/all/users", response_model=List[User])
async def read_users(offset: int = 0, limit: int = 100, session: AsyncSession = Depends(get_session)):
    """📃 Get a paginated list of all users."""
    result = await session.execute(select(User).offset(offset).limit(limit))
    users = result.scalars().all()
    return users


@router.get("/{user_id}/details", response_model=User)
async def read_user(user_id: str, session: AsyncSession = Depends(get_session)):
    """🔍 Get details of a single user by ID."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ============================================================
# ✏️ UPDATE USERS
# ============================================================

@router.patch("/{user_id}/update", response_model=User)
async def update_user(user_id: str, user: User, session: AsyncSession = Depends(get_session)):
    """
    ✏️ Update an existing user.  
    Only fields provided in the body will be updated.
    """
    db_user = await session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    user_data = user.model_dump(exclude_unset=True)
    db_user.sqlmodel_update(user_data)
    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)
    return db_user


# ============================================================
# 🔄 LANGUAGE MANAGEMENT
# ============================================================
@router.patch("/{user_id}/languages", response_model=User)
def update_user_languages(
    user_id: str,
    new_languages: Optional[List[str]] = Body(None),
    add_languages: Optional[List[str]] = Body(None),
    session: Session = Depends(get_session),
):
    """
    🌐 Update or append a user's language list.

    - **new_languages:** Replaces the entire list.
    - **add_languages:** Appends to the current list (ignores duplicates).

    Example usage:
    ```json
    {
      "add_languages": ["French", "Yoruba"]
    }
    ```
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    current_langs = user.languages or []

    if new_languages is not None:
        # Replace the list
        user.languages = list(set(new_languages))
    elif add_languages is not None:
        # Append unique values
        updated = list(set(current_langs + add_languages))
        user.languages = updated

    session.add(user)
    session.commit()
    session.refresh(user)
    return user


# 🗣️ DIALECT MANAGEMEN
@router.patch("/{user_id}/dialects", response_model=User)
def update_user_dialects(
    user_id: str,
    new_dialects: Optional[List[str]] = Body(None),
    add_dialects: Optional[List[str]] = Body(None),
    session: Session = Depends(get_session),
):
    """
    🗣️ Update or append a user's dialect list.

    - **new_dialects:** Replaces the entire list.
    - **add_dialects:** Appends to the current list (ignores duplicates).
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    current_dialects = user.dialects or []

    if new_dialects is not None:
        user.dialects = list(set(new_dialects))
    elif add_dialects is not None:
        updated = list(set(current_dialects + add_dialects))
        user.dialects = updated

    session.add(user)
    session.commit()
    session.refresh(user)
    return user





# ============================================================
# ❌ DELETE USERS
# ============================================================

@router.delete("/{user_id}/delete")
def delete_user(user_id: str, session: Session = Depends(get_session)):
    """🗑️ Delete a user by ID."""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    session.delete(user)
    session.commit()
    return {"ok": True}
