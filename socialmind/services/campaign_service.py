from __future__ import annotations

from typing import TYPE_CHECKING

from socialmind.models.task import Campaign
from socialmind.repositories.account_repository import AccountRepository
from socialmind.repositories.campaign_repository import CampaignRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class CampaignService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = CampaignRepository(session)
        self._account_repo = AccountRepository(session)

    async def get_campaign(self, campaign_id: str) -> Campaign:
        campaign = await self._repo.get_by_id(campaign_id)
        if campaign is None:
            raise ValueError(f"Campaign {campaign_id} not found")
        return campaign

    async def list_campaigns(self, active_only: bool = False) -> list[Campaign]:
        return await self._repo.get_all(active_only=active_only)

    async def create_campaign(
        self,
        name: str,
        description: str | None = None,
        cron_expression: str | None = None,
        account_ids: list[str] | None = None,
        config: dict | None = None,
    ) -> Campaign:
        _ = config
        campaign = await self._repo.create(
            name=name,
            description=description,
            cron_expression=cron_expression,
            is_active=True,
        )

        if account_ids:
            for account_id in account_ids:
                account = await self._account_repo.get_by_id(account_id)
                if account is not None:
                    campaign.accounts.append(account)
            await self._session.flush()

        await self._session.commit()
        return await self.get_campaign(campaign.id)

    async def update_campaign(self, campaign_id: str, **kwargs: object) -> Campaign:
        campaign = await self._repo.update(campaign_id, **kwargs)
        await self._session.commit()
        return await self.get_campaign(campaign.id)

    async def pause(self, campaign_id: str) -> Campaign:
        campaign = await self._repo.pause(campaign_id)
        await self._session.commit()
        return await self.get_campaign(campaign.id)

    async def resume(self, campaign_id: str) -> Campaign:
        campaign = await self._repo.resume(campaign_id)
        await self._session.commit()
        return await self.get_campaign(campaign.id)

    async def delete(self, campaign_id: str) -> None:
        await self._repo.delete(campaign_id)
        await self._session.commit()

    async def add_account(self, campaign_id: str, account_id: str) -> Campaign:
        campaign = await self.get_campaign(campaign_id)
        account = await self._account_repo.get_by_id(account_id)
        if account is None:
            raise ValueError(f"Account {account_id} not found")
        if account not in campaign.accounts:
            campaign.accounts.append(account)
            await self._session.flush()
            await self._session.commit()
        return await self.get_campaign(campaign.id)

    async def remove_account(self, campaign_id: str, account_id: str) -> Campaign:
        campaign = await self.get_campaign(campaign_id)
        campaign.accounts = [a for a in campaign.accounts if a.id != account_id]
        await self._session.flush()
        await self._session.commit()
        return await self.get_campaign(campaign.id)
