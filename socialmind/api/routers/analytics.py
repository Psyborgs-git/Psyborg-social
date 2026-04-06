from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from socialmind.api.dependencies import get_current_user, get_db, get_post_service
from socialmind.models.account import Account, AccountStatus
from socialmind.models.task import Task, TaskStatus
from socialmind.models.user import User
from socialmind.services.post_service import PostService

router = APIRouter()


@router.get("/summary")
async def get_summary(
    _: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    total_accounts = (await db.execute(select(func.count()).select_from(Account))).scalar_one()
    active_accounts = (
        await db.execute(
            select(func.count()).select_from(Account).where(Account.status == AccountStatus.ACTIVE)
        )
    ).scalar_one()
    total_tasks = (await db.execute(select(func.count()).select_from(Task))).scalar_one()

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    tasks_today = (
        await db.execute(
            select(func.count()).select_from(Task).where(Task.created_at >= today_start)
        )
    ).scalar_one()

    success_count = (
        await db.execute(
            select(func.count()).select_from(Task).where(Task.status == TaskStatus.SUCCESS)
        )
    ).scalar_one()
    success_rate = round(success_count / total_tasks, 4) if total_tasks > 0 else 0.0

    return {
        "total_accounts": total_accounts,
        "active_accounts": active_accounts,
        "total_tasks": total_tasks,
        "tasks_today": tasks_today,
        "success_rate": success_rate,
    }


@router.get("/engagement")
async def get_engagement(
    _: Annotated[User, Depends(get_current_user)] = None,
):
    today = datetime.now(timezone.utc).date()
    data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        data.append({
            "date": str(day),
            "likes": 0,
            "comments": 0,
        })
    return data


@router.get("/posts")
async def get_recent_posts(
    limit: int = 20,
    _: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    result = await db.execute(
        select(Task)
        .where(Task.task_type == "post")
        .order_by(Task.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/platforms")
async def get_platforms(
    _: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    result = await db.execute(
        select(Account.platform_id, func.count(Account.id).label("count"))
        .group_by(Account.platform_id)
    )
    rows = result.all()
    return [{"platform": row.platform_id, "count": row.count} for row in rows]
