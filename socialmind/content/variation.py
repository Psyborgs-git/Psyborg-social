from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

HOOKS: list[str] = [
    "Did you know that",
    "The truth about",
    "Stop doing this if you want",
    "Why most people fail at",
    "This changed everything for me:",
    "Unpopular opinion:",
    "What nobody tells you about",
]

CTAS: list[str] = [
    "Drop a 🔥 if you agree",
    "What do you think? Comment below",
    "Tag someone who needs to see this",
    "Save this for later",
    "Follow for more tips like this",
    "Share with a friend who needs this",
]


class ContentVariationEngine:
    """Adds variation signals to DSPy prompts to prevent repetitive output."""

    @staticmethod
    def get_variation_context(account_id: str, post_number: int) -> dict[str, str]:
        """Return variation hints for the DSPy post generator."""
        rng = random.Random(f"{account_id}-{post_number}")
        return {
            "suggested_hook": rng.choice(HOOKS),
            "suggested_cta": rng.choice(CTAS),
            "format": rng.choice(["list", "story", "opinion", "question", "tip"]),
            "opening_style": rng.choice(["question", "statement", "stat", "anecdote"]),
        }

    @staticmethod
    async def get_post_number(account_id: str, db_session: AsyncSession) -> int:
        """Count how many posts this account has made (for seeding variation)."""
        from sqlalchemy import func, select

        from socialmind.models.media import PostRecord

        result = await db_session.execute(
            select(func.count()).where(PostRecord.account_id == account_id)
        )
        return result.scalar() or 0

