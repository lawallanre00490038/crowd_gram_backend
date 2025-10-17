from fastapi import FastAPI
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from src.db import events

import os
from src.errors import register_all_errors
from src.middleware import register_middleware
from src.db.database import create_tables
from src.routers import users, submissions, status, telegram, projects, reviewer, agent

load_dotenv()


version = "v1"

description = """
Aiogram Telegram Bot Backend API.
This API allows you to manage users, projects, submissions, and more for the Aiogram Telegram Bot platform.
"""

version_prefix = f"/api/{version}"



@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        pass
    except Exception as e:
        print(f"Error connecting to Redis: {e}")

    await create_tables()
    yield



app = FastAPI(
    lifespan=lifespan,
    title="Aiogram Telegram Bot Backend",
    description=description,
    version=version,
    license_info={"name": "MIT License", "url": "https://opensource.org/license/mit"},
    contact={
        "name": "EqualyzAI",
        "url": "https://equalyz.ai/",
        "email": "uche@equalyz.ai",
    },
    terms_of_service="https://equalyz.ai/about-us/",
    openapi_url=f"{version_prefix}/openapi.json",
    docs_url=f"{version_prefix}/docs",
    redoc_url=f"{version_prefix}/redoc"
)




# Register error handlers and middleware
register_all_errors(app)
register_middleware(app)

@app.get("/")
async def root():
    return {
        "message": "FastAPI Crowdsource Backend is running!"
    }
    

app.include_router(users.router,  prefix=f"{version_prefix}/user", tags=["Users"])
app.include_router(telegram.router, prefix=f"{version_prefix}/telegram", tags=["Telegram"])
app.include_router(projects.router, prefix=f"{version_prefix}/project", tags=["Projects"])
app.include_router(agent.router, prefix=f"{version_prefix}/agent", tags=["Tasks"])
app.include_router(submissions.router, prefix=f"{version_prefix}/submission", tags=["Agent Submissions"])
app.include_router(reviewer.router, prefix=f"{version_prefix}/reviewer", tags=["Reviewer"])
app.include_router(status.router, prefix=f"{version_prefix}/status", tags=["Status"])


    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0",
        port=10000,
        reload=True
    )