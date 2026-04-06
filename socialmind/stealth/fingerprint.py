from __future__ import annotations

import random


class FingerprintProfile:
    """A consistent fingerprint profile assigned to an account."""

    @staticmethod
    def generate(account_id: str) -> dict:
        """Generate a deterministic but realistic fingerprint for an account."""
        rng = random.Random(account_id)  # Seeded: same account → same fingerprint
        return {
            "user_agent": FingerprintProfile._pick_ua(rng),
            "viewport": rng.choice(
                [
                    {"width": 390, "height": 844},  # iPhone 14
                    {"width": 412, "height": 915},  # Pixel 7
                    {"width": 393, "height": 852},  # iPhone 15
                ]
            ),
            "hardware_concurrency": rng.choice([6, 8]),
            "device_memory": rng.choice([4, 8]),
            "webgl_renderer": rng.choice(
                [
                    "Adreno (TM) 730",
                    "Apple GPU",
                    "Mali-G78",
                ]
            ),
            "timezone": rng.choice(
                [
                    "America/New_York",
                    "America/Los_Angeles",
                    "America/Chicago",
                    "America/Denver",
                ]
            ),
            "screen": rng.choice(
                [
                    {"width": 390, "height": 844, "dpr": 3},
                    {"width": 412, "height": 915, "dpr": 2.625},
                ]
            ),
            "color_depth": 24,
            "languages": ["en-US", "en"],
        }

    @staticmethod
    def _pick_ua(rng: random.Random) -> str:
        """Pick a real, high-frequency user agent string."""
        uas = [
            (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
            ),
            (
                "Mozilla/5.0 (Linux; Android 14; Pixel 7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
            ),
            (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
            ),
        ]
        return rng.choice(uas)


async def apply_stealth(page: object, fingerprint: dict) -> None:
    """Apply all stealth patches to a Playwright page."""
    try:
        from playwright_stealth import stealth_async  # type: ignore[import-untyped]

        await stealth_async(page)  # type: ignore[arg-type]
    except ImportError:
        pass  # playwright_stealth not installed — skip

    await page.set_extra_http_headers(  # type: ignore[attr-defined]
        {
            "Accept-Language": "en-US,en;q=0.9",
            'sec-ch-ua': '"Chromium";v="124", "Google Chrome";v="124"',
            "sec-ch-ua-mobile": "?1",
            'sec-ch-ua-platform': '"Android"',
        }
    )
    await page.set_viewport_size(fingerprint["viewport"])  # type: ignore[attr-defined]
    hw = fingerprint["hardware_concurrency"]
    dm = fingerprint["device_memory"]
    await page.add_init_script(  # type: ignore[attr-defined]
        f"""
        Object.defineProperty(navigator, 'hardwareConcurrency', {{
            get: () => {hw}
        }});
        Object.defineProperty(navigator, 'deviceMemory', {{
            get: () => {dm}
        }});
        """
    )
