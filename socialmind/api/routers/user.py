from __future__ import annotations

from typing import Annotated

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from socialmind.api.dependencies import get_current_user, get_db
from socialmind.models.user import User

router = APIRouter()


class UserSettingsResponse(BaseModel):
    username: str
    email: str | None = None
    notifications_enabled: bool = True


class UserSettingsUpdate(BaseModel):
    username: str | None = None
    email: str | None = None
    notifications_enabled: bool | None = None


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str


@router.get("/settings", response_model=UserSettingsResponse)
async def get_user_settings(
    current_user: Annotated[User, Depends(get_current_user)],
):
    return UserSettingsResponse(username=current_user.username)


@router.put("/settings", response_model=UserSettingsResponse)
async def update_user_settings(
    body: UserSettingsUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if body.username:
        current_user.username = body.username

    await db.commit()
    await db.refresh(current_user)

    return UserSettingsResponse(
        username=current_user.username,
        email=body.email,
        notifications_enabled=(
            body.notifications_enabled
            if body.notifications_enabled is not None
            else True
        ),
    )


@router.put("/password")
async def change_password(
    body: PasswordChangeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if not bcrypt.checkpw(
        body.old_password.encode("utf-8"),
        current_user.hashed_password.encode("utf-8"),
    ):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    current_user.hashed_password = bcrypt.hashpw(
        body.new_password.encode("utf-8"), bcrypt.gensalt(rounds=12)
    ).decode("utf-8")
    await db.commit()

    return {"message": "Password updated successfully"}
