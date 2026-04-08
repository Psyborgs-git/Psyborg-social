from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from socialmind.models.account import Account
from socialmind.models.task import Campaign


class CampaignRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, campaign_id: str) -> Campaign | None:
        result = await self._session.execute(
            select(Campaign)
            .options(selectinload(Campaign.accounts).selectinload(Account.platform))
            .where(Campaign.id == campaign_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, active_only: bool = False) -> list[Campaign]:
        stmt = select(Campaign).options(
            selectinload(Campaign.accounts).selectinload(Account.platform)
        )
        if active_only:
            stmt = stmt.where(Campaign.is_active.is_(True))
        result = await self._session.execute(stmt)
        return list(result.scalars())

    async def create(self, **kwargs: object) -> Campaign:
        campaign = Campaign(**kwargs)
        self._session.add(campaign)
        await self._session.flush()
        await self._session.refresh(campaign)
        return campaign

    async def update(self, campaign_id: str, **kwargs: object) -> Campaign:
        campaign = await self.get_by_id(campaign_id)
        if campaign is None:
            raise ValueError(f"Campaign {campaign_id} not found")
        for key, value in kwargs.items():
            setattr(campaign, key, value)
        await self._session.flush()
        return campaign

    async def delete(self, campaign_id: str) -> None:
        campaign = await self.get_by_id(campaign_id)
        if campaign is not None:
            await self._session.delete(campaign)
            await self._session.flush()

    async def pause(self, campaign_id: str) -> Campaign:
        return await self.update(campaign_id, is_active=False)

    async def resume(self, campaign_id: str) -> Campaign:
        return await self.update(campaign_id, is_active=True)
