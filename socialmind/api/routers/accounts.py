from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from socialmind.api.dependencies import (
    get_current_user,
    get_account_service,
    get_post_service,
    get_db,
)
from socialmind.models.account import Account
from socialmind.models.user import User
from socialmind.services.account_service import AccountService
from socialmind.services.post_service import PostService

router = APIRouter()


class AccountCreate(BaseModel):
    platform: str
    username: str
    password: str
    proxy_url: str | None = None


class AccountUpdate(BaseModel):
    display_name: str | None = None
    daily_action_limit: int | None = None


class PauseRequest(BaseModel):
    reason: str | None = None


class PlatformResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    slug: str
    display_name: str


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    username: str
    platform_id: str
    platform: PlatformResponse | None = None
    status: str
    display_name: str | None = None
    daily_action_limit: int
    warmup_phase: bool
    created_at: datetime


@router.get("/", response_model=list[AccountResponse])
async def list_accounts(
    platform: str | None = None,
    status: str | None = None,
    _: Annotated[User, Depends(get_current_user)] = None,
    account_service: Annotated[AccountService, Depends(get_account_service)] = None,
):
    accounts = await account_service.list_accounts(platform=platform, status=status)
    return accounts


@router.post("/", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    body: AccountCreate,
    _: Annotated[User, Depends(get_current_user)] = None,
    account_service: Annotated[AccountService, Depends(get_account_service)] = None,
):
    account = await account_service.create_account(
        platform=body.platform,
        username=body.username,
        credentials={"password": body.password},
        proxy_url=body.proxy_url,
    )
    return account


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: str,
    _: Annotated[User, Depends(get_current_user)] = None,
    account_service: Annotated[AccountService, Depends(get_account_service)] = None,
):
    account = await account_service.get_account(account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.patch("/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: str,
    body: AccountUpdate,
    _: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    result = await db.execute(
        select(Account)
        .options(selectinload(Account.platform))
        .where(Account.id == account_id)
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")

    if body.display_name is not None:
        account.display_name = body.display_name
    if body.daily_action_limit is not None:
        account.daily_action_limit = body.daily_action_limit

    await db.commit()
    refreshed = await db.execute(
        select(Account)
        .options(selectinload(Account.platform))
        .where(Account.id == account_id)
    )
    return refreshed.scalar_one()


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: str,
    _: Annotated[User, Depends(get_current_user)] = None,
    account_service: Annotated[AccountService, Depends(get_account_service)] = None,
):
    await account_service.delete(account_id)


@router.post("/{account_id}/pause")
async def pause_account(
    account_id: str,
    body: PauseRequest | None = None,
    _: Annotated[User, Depends(get_current_user)] = None,
    account_service: Annotated[AccountService, Depends(get_account_service)] = None,
):
    account = await account_service.pause(
        account_id,
        reason=body.reason if body is not None else None,
    )
    return {"id": account_id, "status": "paused"}


@router.post("/{account_id}/resume")
async def resume_account(
    account_id: str,
    _: Annotated[User, Depends(get_current_user)] = None,
    account_service: Annotated[AccountService, Depends(get_account_service)] = None,
):
    account = await account_service.resume(account_id)
    return {"id": account_id, "status": "resumed"}


@router.get("/{account_id}/posts")
async def get_recent_posts(
    account_id: str,
    limit: int = 10,
    _: Annotated[User, Depends(get_current_user)] = None,
    post_service: Annotated[PostService, Depends(get_post_service)] = None,
):
    posts = await post_service.get_recent_posts(account_id, limit=limit)
    return posts


@router.get("/{account_id}/rate-limits")
async def get_rate_limits(
    account_id: str,
    _: Annotated[User, Depends(get_current_user)] = None,
    account_service: Annotated[AccountService, Depends(get_account_service)] = None,
):
    usage = await account_service.get_rate_limit_usage(account_id)
    return usage
