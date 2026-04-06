from __future__ import annotations

import asyncio
import math
import random


class TimingEngine:
    """
    Generates human-like delays using log-normal distributions.
    All values are in seconds.
    """

    # (mean, std_dev) tuples for each action type
    DELAY_PROFILES: dict[str, tuple[float, float]] = {
        "post": (8.0, 3.0),
        "comment": (5.0, 2.5),
        "like": (0.8, 0.4),
        "follow": (1.5, 0.7),
        "dm": (12.0, 5.0),
        "typing": (0.1, 0.03),
        "scroll": (2.5, 1.0),
        "click": (0.4, 0.2),
        "form_fill": (3.0, 1.5),
        "form_submit": (1.5, 0.8),
        "page_load": (1.5, 0.5),
        "session_start": (30.0, 15.0),
        "unfollow": (1.2, 0.6),
        "story_view": (3.0, 1.5),
        "search": (2.0, 1.0),
        "reel": (6.0, 2.0),
    }

    @classmethod
    async def delay(cls, action_type: str, multiplier: float = 1.0) -> None:
        """Apply a human-like delay for the given action type."""
        mean, std = cls.DELAY_PROFILES.get(action_type, (2.0, 1.0))
        mean *= multiplier
        sigma = math.sqrt(math.log(1 + (std / mean) ** 2))
        mu = math.log(mean) - sigma**2 / 2
        delay_seconds = random.lognormvariate(mu, sigma)
        # Clamp to reasonable bounds
        delay_seconds = max(0.1, min(delay_seconds, mean * 4))
        await asyncio.sleep(delay_seconds)

    @classmethod
    async def type_text(cls, page: object, selector: str, text: str) -> None:
        """Type text with per-character human delays, including occasional mistakes."""
        element = page.locator(selector)  # type: ignore[attr-defined]
        for char in text:
            if random.random() < 0.02:  # 2% typo rate
                wrong_char = random.choice("qwertyuiopasdfghjklzxcvbnm")
                await element.press(wrong_char)
                await asyncio.sleep(random.uniform(0.1, 0.4))
                await element.press("Backspace")
                await asyncio.sleep(random.uniform(0.05, 0.2))
            await element.type(char, delay=random.lognormvariate(-2.3, 0.5) * 1000)

    @classmethod
    async def human_scroll(cls, page: object, scroll_count: int = 3) -> None:
        """Scroll through a feed in a human-like pattern."""
        for _ in range(scroll_count):
            scroll_amount = random.randint(300, 800)
            await page.mouse.wheel(0, scroll_amount)  # type: ignore[attr-defined]
            await cls.delay("scroll")
            if random.random() < 0.2:
                await page.mouse.wheel(0, -random.randint(50, 200))  # type: ignore[attr-defined]
                await asyncio.sleep(random.uniform(0.3, 0.8))


def with_human_delay(action_type: str, multiplier: float = 1.0):
    """Decorator that applies a human-like delay before calling the wrapped async function."""
    import functools

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            await TimingEngine.delay(action_type, multiplier)
            return await func(*args, **kwargs)

        return wrapper

    return decorator
