from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from socialmind.models.account import Account, AccountStatus


class AccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, account_id: str) -> Account | None:
        return await self._session.get(Account, account_id)

    async def get_all(
        self,
        platform_slug: str | None = None,
        status: str | None = None,
    ) -> list[Account]:
        stmt = select(Account)
        if platform_slug is not None:
            from socialmind.models.platform import Platform

            stmt = stmt.join(Platform).where(Platform.slug == platform_slug)
        if status is not None:
            stmt = stmt.where(Account.status == status)
        result = await self._session.execute(stmt)
        return list(result.scalars())

    async def get_active_by_platform(self, platform_slug: str) -> list[Account]:
        from socialmind.models.platform import Platform

        result = await self._session.execute(
            select(Account)
            .join(Platform)
            .where(Platform.slug == platform_slug)
            .where(Account.status == AccountStatus.ACTIVE)
        )
        return list(result.scalars())

    async def create(self, **kwargs: object) -> Account:
        account = Account(**kwargs)
        self._session.add(account)
        await self._session.flush()
        await self._session.refresh(account)
        return account

    async def update(self, account_id: str, **kwargs: object) -> Account:
        account = await self.get_by_id(account_id)
        if account is None:
            raise ValueError(f"Account {account_id} not found")
        for key, value in kwargs.items():
            setattr(account, key, value)
        await self._session.flush()
        return account

    async def update_status(
        self, account_id: str, status: AccountStatus
    ) -> Account:
        return await self.update(account_id, status=status)

    async def delete(self, account_id: str) -> None:
        account = await self.get_by_id(account_id)
        if account is not None:
            await self._session.delete(account)
            await self._session.flush()

