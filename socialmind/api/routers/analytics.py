from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from socialmind.api.dependencies import get_current_user, get_db
from socialmind.models.account import Account, AccountStatus
from socialmind.models.platform import Platform
from socialmind.models.task import Task, TaskStatus
from socialmind.models.user import User

router = APIRouter()


@router.get("/summary")
async def get_summary(
    _: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    total_accounts = (
        await db.execute(select(func.count()).select_from(Account))
    ).scalar_one()
    active_accounts = (
        await db.execute(
            select(func.count())
            .select_from(Account)
            .where(Account.status == AccountStatus.ACTIVE)
        )
    ).scalar_one()
    total_tasks = (
        await db.execute(select(func.count()).select_from(Task))
    ).scalar_one()

    today_start = datetime.now(UTC).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    tasks_today = (
        await db.execute(
            select(func.count()).select_from(Task).where(Task.created_at >= today_start)
        )
    ).scalar_one()
    posts_today = (
        await db.execute(
            select(func.count())
            .select_from(Task)
            .where(Task.task_type == "post")
            .where(Task.created_at >= today_start)
        )
    ).scalar_one()
    dms_replied = (
        await db.execute(
            select(func.count())
            .select_from(Task)
            .where(Task.task_type == "reply_dm")
            .where(Task.status == TaskStatus.SUCCESS)
            .where(Task.created_at >= today_start)
        )
    ).scalar_one()
    tasks_running = (
        await db.execute(
            select(func.count())
            .select_from(Task)
            .where(Task.status == TaskStatus.RUNNING)
        )
    ).scalar_one()

    success_count = (
        await db.execute(
            select(func.count())
            .select_from(Task)
            .where(Task.status == TaskStatus.SUCCESS)
        )
    ).scalar_one()
    success_rate = (
        round((success_count / total_tasks) * 100, 1) if total_tasks > 0 else 0.0
    )

    return {
        "total_accounts": total_accounts,
        "active_accounts": active_accounts,
        "total_tasks": total_tasks,
        "tasks_today": tasks_today,
        "posts_today": posts_today,
        "dms_replied": dms_replied,
        "tasks_running": tasks_running,
        "success_rate": success_rate,
    }


@router.get("/engagement")
async def get_engagement(
    _: Annotated[User, Depends(get_current_user)] = None,
):
    today = datetime.now(UTC).date()
    data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        data.append(
            {
                "date": str(day),
                "likes": 0,
                "comments": 0,
                "value": 0,
            }
        )
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
        select(
            Platform.slug.label("platform"),
            Platform.display_name.label("name"),
            func.count(Account.id).label("count"),
        )
        .join(Account, Account.platform_id == Platform.id)
        .group_by(Platform.slug, Platform.display_name)
    )
    rows = result.all()
    return [
        {
            "platform": row.platform,
            "name": row.name,
            "count": row.count,
            "value": row.count,
        }
        for row in rows
    ]
