from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from socialmind.stealth.fingerprint import FingerprintProfile, apply_stealth

if TYPE_CHECKING:
    from playwright.async_api import Browser, BrowserContext

    from socialmind.models.account import Account
    from socialmind.models.proxy import Proxy

_context_cache: dict[str, "BrowserContext"] = {}
_browser: "Browser | None" = None
_browser_lock = asyncio.Lock()


async def get_shared_browser() -> "Browser":
    """Return the singleton Playwright browser instance, launching it if needed."""
    global _browser
    async with _browser_lock:
        if _browser is None or not _browser.is_connected():
            from playwright.async_api import async_playwright

            playwright = await async_playwright().start()
            _browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
    return _browser


class BrowserContextFactory:
    """Manages per-account isolated browser contexts with stealth patching."""

    @staticmethod
    async def get_or_create(
        account: "Account",
        proxy: "Proxy | None",
    ) -> "BrowserContext":
        """Return or create an isolated browser context for the given account."""
        account_id = account.id

        existing = _context_cache.get(account_id)
        if existing is not None and not existing.is_closed():
            return existing

        fingerprint = FingerprintProfile.generate(account_id)
        browser = await get_shared_browser()

        proxy_config: dict | None = None
        if proxy:
            proxy_config = {
                "server": proxy.as_url(),
            }
            if proxy.username:
                from socialmind.security.encryption import get_vault

                proxy_config["username"] = proxy.username
                if proxy.password_encrypted:
                    pw_data = get_vault().decrypt(proxy.password_encrypted)
                    proxy_config["password"] = pw_data.get("password", "")

        ctx = await browser.new_context(
            user_agent=fingerprint["user_agent"],
            viewport=fingerprint["viewport"],
            device_scale_factor=fingerprint["screen"]["dpr"],
            locale="en-US",
            timezone_id=fingerprint["timezone"],
            proxy=proxy_config,
            storage_state=account.sessions[0].browser_storage_state
            if account.sessions
            else None,
        )

        ctx.on(
            "page",
            lambda page: asyncio.ensure_future(apply_stealth(page, fingerprint)),
        )

        _context_cache[account_id] = ctx
        return ctx

    @staticmethod
    async def save_state(account: "Account") -> None:
        """Persist browser cookies and storage to the account session after each use."""
        ctx = _context_cache.get(account.id)
        if ctx and not ctx.is_closed() and account.sessions:
            state = await ctx.storage_state()
            session = account.sessions[0]
            session.cookies = state.get("cookies", [])
            session.local_storage = state.get("origins", [])

    @staticmethod
    async def close(account_id: str) -> None:
        """Close and remove the context for an account."""
        ctx = _context_cache.pop(account_id, None)
        if ctx and not ctx.is_closed():
            await ctx.close()
