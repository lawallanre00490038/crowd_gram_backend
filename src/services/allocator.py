"""
Allocator service that performs allocation for a Project.
Usage:
    from sqlmodel import Session
    allocate_project(project_id, user_ids, user_emails, session)

Behaviour:
- respects per-user quota
- respects per-prompt max_reuses (prompt.max_reuses or project.reuse_count)
- idempotent for existing (task,user) pairs
"""
from collections import Counter, deque
import random
from typing import List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from src.db.models import (
    Project, Prompt, Task, AgentAllocation,
    Status
)


async def allocate_project(
    project_id: str,
    user_ids: List[str],
    user_emails: List[str],
    session: AsyncSession
) -> List[AgentAllocation]:
    """
    Allocate tasks from a project to a set of users.
    """
    # ------------------- 1. Load project -------------------
    project = await session.get(Project, project_id)
    if not project:
        raise ValueError("Project not found")

    # ------------------- 2. Load prompts with tasks -------------------
    prompts_result = await session.execute(
        select(Prompt)
        .options(selectinload(Prompt.tasks))
        .where(Prompt.project_id == project_id)
    )
    prompts = prompts_result.scalars().all()

    # Build slot queue based on prompt max_reuses
    slot_list = []
    for prompt in prompts:
        max_r = prompt.max_reuses if prompt.max_reuses is not None else project.reuse_count
        max_r = max_r or 1
        remaining = max(0, max_r - (prompt.current_reuses or 0))
        slot_list.extend([prompt.id] * remaining)

    random.shuffle(slot_list)
    slot_queue = deque(slot_list)

    # ------------------- 3. Load existing allocations -------------------
    existing_alloc_result = await session.execute(
        select(AgentAllocation).where(AgentAllocation.project_id == project_id)
    )
    existing_allocations = existing_alloc_result.scalars().all()

    allocated_map = {}
    existing_pairs = set()
    for alloc in existing_allocations:
        allocated_map[alloc.user_id] = allocated_map.get(alloc.user_id, 0) + 1
        existing_pairs.add((alloc.task_id, alloc.user_id))

    new_allocations: List[AgentAllocation] = []

    # ------------------- 4. Round-robin allocate prompts to users -------------------
    for idx, user_id in enumerate(user_ids):
        user_email = user_emails[idx]
        already = allocated_map.get(user_id, 0)
        to_assign = max(0, project.agent_quota - already)

        while to_assign > 0 and slot_queue:
            prompt_id = slot_queue.popleft()

            # Check if a task for this prompt exists, else create one
            task_result = await session.execute(
                select(Task).where(Task.project_id == project_id, Task.prompt_id == prompt_id)
            )
            task = task_result.scalars().first()

            if not task:
                task = Task(
                    project_id=project_id,
                    prompt_id=prompt_id,
                    status=Status.pending
                )
                session.add(task)
                await session.flush()  # ensure task.id is available

            if (task.id, user_id) in existing_pairs:
                continue  # skip duplicates

            alloc = AgentAllocation(
                project_id=project_id,
                task_id=task.id,
                user_id=user_id,
                user_email=user_email,
                assigned_at=datetime.utcnow(),
                status=Status.assigned
            )
            session.add(alloc)
            new_allocations.append(alloc)

            existing_pairs.add((task.id, user_id))
            allocated_map[user_id] = allocated_map.get(user_id, 0) + 1
            to_assign -= 1

    # ------------------- 5. Update prompt.current_reuses -------------------
    counts = Counter()
    for alloc in new_allocations:
        task = await session.get(Task, alloc.task_id)
        if task:
            counts[task.prompt_id] += 1

    for prompt_id, cnt in counts.items():
        prompt = await session.get(Prompt, prompt_id)
        if prompt:
            prompt.current_reuses = (prompt.current_reuses or 0) + cnt
            session.add(prompt)

    # ------------------- 6. Commit and refresh allocations -------------------
    await session.commit()
    for alloc in new_allocations:
        await session.refresh(alloc)

    return new_allocations
