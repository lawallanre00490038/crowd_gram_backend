# database.py
import os
from dotenv import load_dotenv
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL_ASYNC = os.getenv("DATABASE_URL_ASYNC")

DATABASE_URL = DATABASE_URL_ASYNC


# Convert URL to async driver
# url_obj = make_url(DATABASE_URL)
# ASYNC_DATABASE_URL = str(url_obj.set(drivername="postgresql+asyncpg"))


# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # enable logging to debug
    pool_pre_ping=True
)

# Async session factory
async_session_maker = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_session():
    async with async_session_maker() as session:
        yield session

# Create tables
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
