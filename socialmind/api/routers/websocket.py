from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from socialmind.api.dependencies import get_db
from socialmind.models.task import TaskStatus
from socialmind.repositories.task_repository import TaskRepository

router = APIRouter()

_TERMINAL_STATUSES = {TaskStatus.SUCCESS, TaskStatus.FAILED}
_POLL_SECONDS = 1
_MAX_POLL_SECONDS = 300


@router.websocket("/ws/tasks/{task_id}/logs")
async def task_logs_ws(
    websocket: WebSocket,
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    await websocket.accept()
    repo = TaskRepository(db)

    task = await db.get(__import__("socialmind.models.task", fromlist=["Task"]).Task, task_id)
    if task is None:
        await websocket.send_text(json.dumps({"error": "Task not found"}))
        await websocket.close()
        return

    seen_ids: set[str] = set()
    elapsed = 0

    try:
        while elapsed < _MAX_POLL_SECONDS:
            logs = await repo.get_logs(task_id)
            for log in logs:
                if log.id not in seen_ids:
                    seen_ids.add(log.id)
                    await websocket.send_text(
                        json.dumps(
                            {
                                "id": log.id,
                                "level": log.level,
                                "message": log.message,
                                "timestamp": log.timestamp.isoformat()
                                if isinstance(log.timestamp, datetime)
                                else str(log.timestamp),
                            }
                        )
                    )

            await db.refresh(task)
            if task.status in _TERMINAL_STATUSES:
                break

            await asyncio.sleep(_POLL_SECONDS)
            elapsed += _POLL_SECONDS
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
