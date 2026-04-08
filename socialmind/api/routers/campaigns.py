from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from socialmind.api.dependencies import (
    get_campaign_service,
    get_current_user,
)
from socialmind.models.user import User
from socialmind.services.campaign_service import CampaignService

router = APIRouter()


class CampaignCreate(BaseModel):
    name: str
    description: str | None = None
    cron_expression: str | None = None
    account_ids: list[str] = Field(default_factory=list)


class CampaignUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    cron_expression: str | None = None


class PlatformResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    slug: str
    display_name: str


class CampaignAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    username: str
    display_name: str | None = None
    platform_id: str
    status: str
    platform: PlatformResponse | None = None


class CampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    description: str | None = None
    is_active: bool
    cron_expression: str | None = None
    accounts: list[CampaignAccountResponse] = Field(default_factory=list)
    created_at: datetime


@router.get("/", response_model=list[CampaignResponse])
async def list_campaigns(
    active_only: bool = False,
    _: Annotated[User, Depends(get_current_user)] = None,
    campaign_service: Annotated[CampaignService, Depends(get_campaign_service)] = None,
):
    return await campaign_service.list_campaigns(active_only=active_only)


@router.post("/", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    body: CampaignCreate,
    _: Annotated[User, Depends(get_current_user)] = None,
    campaign_service: Annotated[CampaignService, Depends(get_campaign_service)] = None,
):
    return await campaign_service.create_campaign(
        name=body.name,
        description=body.description,
        cron_expression=body.cron_expression,
        account_ids=body.account_ids,
        config={},
    )


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: str,
    _: Annotated[User, Depends(get_current_user)] = None,
    campaign_service: Annotated[CampaignService, Depends(get_campaign_service)] = None,
):
    campaign = await campaign_service.get_campaign(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.patch("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: str,
    body: CampaignUpdate,
    _: Annotated[User, Depends(get_current_user)] = None,
    campaign_service: Annotated[CampaignService, Depends(get_campaign_service)] = None,
):
    kwargs = {k: v for k, v in body.model_dump().items() if v is not None}
    campaign = await campaign_service.update_campaign(campaign_id, **kwargs)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: str,
    _: Annotated[User, Depends(get_current_user)] = None,
    campaign_service: Annotated[CampaignService, Depends(get_campaign_service)] = None,
):
    await campaign_service.delete(campaign_id)


@router.post("/{campaign_id}/pause")
async def pause_campaign(
    campaign_id: str,
    _: Annotated[User, Depends(get_current_user)] = None,
    campaign_service: Annotated[CampaignService, Depends(get_campaign_service)] = None,
):
    await campaign_service.pause(campaign_id)
    return {"id": campaign_id, "status": "paused"}


@router.post("/{campaign_id}/resume")
async def resume_campaign(
    campaign_id: str,
    _: Annotated[User, Depends(get_current_user)] = None,
    campaign_service: Annotated[CampaignService, Depends(get_campaign_service)] = None,
):
    await campaign_service.resume(campaign_id)
    return {"id": campaign_id, "status": "active"}


@router.post("/{campaign_id}/activate")
async def activate_campaign(
    campaign_id: str,
    _: Annotated[User, Depends(get_current_user)] = None,
    campaign_service: Annotated[CampaignService, Depends(get_campaign_service)] = None,
):
    await campaign_service.resume(campaign_id)
    return {"id": campaign_id, "status": "active"}


@router.post("/{campaign_id}/deactivate")
async def deactivate_campaign(
    campaign_id: str,
    _: Annotated[User, Depends(get_current_user)] = None,
    campaign_service: Annotated[CampaignService, Depends(get_campaign_service)] = None,
):
    await campaign_service.pause(campaign_id)
    return {"id": campaign_id, "status": "paused"}


@router.post("/{campaign_id}/accounts/{account_id}", response_model=CampaignResponse)
async def add_account_to_campaign(
    campaign_id: str,
    account_id: str,
    _: Annotated[User, Depends(get_current_user)] = None,
    campaign_service: Annotated[CampaignService, Depends(get_campaign_service)] = None,
):
    try:
        return await campaign_service.add_account(campaign_id, account_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{campaign_id}/accounts/{account_id}", response_model=CampaignResponse)
async def remove_account_from_campaign(
    campaign_id: str,
    account_id: str,
    _: Annotated[User, Depends(get_current_user)] = None,
    campaign_service: Annotated[CampaignService, Depends(get_campaign_service)] = None,
):
    try:
        return await campaign_service.remove_account(campaign_id, account_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
