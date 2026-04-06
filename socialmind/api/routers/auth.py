from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext

from socialmind.api.dependencies import get_db, get_current_user
from socialmind.models.user import User
from socialmind.security.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    AuthenticationError,
)

router = APIRouter()

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/token")
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()

    if user is None or not _pwd_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account is inactive")

    return {
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
        "refresh_token": create_refresh_token(user.id),
    }


@router.post("/refresh")
async def refresh(body: RefreshRequest):
    try:
        payload = decode_token(body.refresh_token)
    except AuthenticationError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    return {"access_token": create_access_token(user_id), "token_type": "bearer"}


@router.post("/logout")
async def logout(_: Annotated[User, Depends(get_current_user)]):
    return {"message": "Logged out"}
