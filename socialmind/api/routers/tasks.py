from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from socialmind.api.dependencies import (
    get_current_user,
    get_post_service,
    get_db,
)
from socialmind.models.task import Task, TaskStatus
from socialmind.models.user import User
from socialmind.repositories.task_repository import TaskRepository
from socialmind.services.post_service import PostService

router = APIRouter()


class TaskCreate(BaseModel):
    account_id: str
    task_type: str
    config: dict = {}
    scheduled_at: str | None = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    account_id: str
    task_type: str
    status: str
    config: dict
    scheduled_at: datetime | None
    created_at: datetime


class TaskLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    task_id: str
    level: str
    message: str
    timestamp: datetime


@router.get("/", response_model=list[TaskResponse])
async def list_tasks(
    account_id: str | None = None,
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
    _: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    repo = TaskRepository(db)
    if account_id:
        tasks = await repo.get_for_account(account_id, limit=limit)
    else:
        from sqlalchemy import select
        from socialmind.models.task import Task as TaskModel
        stmt = select(TaskModel).limit(limit).offset(offset)
        if status:
            stmt = stmt.where(TaskModel.status == status)
        result = await db.execute(stmt)
        tasks = result.scalars().all()
    return tasks


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    body: TaskCreate,
    _: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    post_service: Annotated[PostService, Depends(get_post_service)] = None,
):
    repo = TaskRepository(db)
    if body.task_type == "post":
        task = await post_service.create_post_task(
            account_id=body.account_id,
            prompt=body.config.get("prompt", ""),
            post_type=body.config.get("post_type", "feed"),
            include_image=body.config.get("include_image", True),
            schedule_at=body.scheduled_at,
        )
    else:
        scheduled_at = None
        if body.scheduled_at:
            scheduled_at = datetime.fromisoformat(body.scheduled_at)
        task = await repo.create(
            account_id=body.account_id,
            task_type=body.task_type,
            config=body.config,
            scheduled_at=scheduled_at,
        )
    return task


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    _: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_task(
    task_id: str,
    _: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    repo = TaskRepository(db)
    await repo.update_status(task_id, TaskStatus.FAILED)


@router.get("/{task_id}/logs", response_model=list[TaskLogResponse])
async def get_task_logs(
    task_id: str,
    _: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    repo = TaskRepository(db)
    logs = await repo.get_logs(task_id)
    return logs
