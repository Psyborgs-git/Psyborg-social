# Anti-Detection & Stealth Infrastructure

The stealth layer sits between all automation actions and the platform adapters. Its job is to make automated behavior statistically indistinguishable from genuine human usage. This document covers the full strategy.

---

## Threat Model

Platforms detect bots using several signal categories:

| Signal Category | Examples | Our Mitigation |
|---|---|---|
| **Network fingerprint** | IP reputation, ASN, datacenter IP | Residential/mobile proxies |
| **TLS fingerprint** | JA3/JA4 hash of TLS handshake | `curl-cffi` (browser TLS impersonation) |
| **Browser fingerprint** | Canvas, WebGL, AudioContext, fonts | `playwright-stealth` patches |
| **Behavioral timing** | Click intervals, scroll patterns, typing speed | Gaussian timing engine |
| **Session patterns** | Login time, session duration, action frequency | Rate limiting, warmup schedules |
| **Device consistency** | Same device ID across sessions | Persistent device profiles |
| **Request patterns** | API endpoint sequence, parameter patterns | Mimicking official app request flows |
| **Content patterns** | Repetitive posts, identical captions | DSPy variation + persona diversity |

---

## 1. Proxy Infrastructure

### Proxy Types (Priority Order)

```
1. Mobile proxies (4G/5G)   — Most trusted, highest cost, best for IG/TikTok
2. Residential proxies       — Home IP addresses via peer networks
3. ISP proxies               — Static residential from real ISPs
4. Datacenter proxies        — Avoid for Instagram/TikTok; OK for Reddit/YouTube
```

**Recommended providers:**
- **Bright Data** — Residential + mobile pools, good uptime
- **Oxylabs** — Residential pool
- **IPRoyal** — Mobile proxies, affordable
- **Smartproxy** — Mid-tier residential

### Proxy Pool Manager

```python
# socialmind/stealth/proxy.py
from dataclasses import dataclass
import redis.asyncio as redis
import random

class ProxyPoolManager:
    """
    Manages a pool of proxies with:
    - Health tracking (fail count, last check)
    - Sticky assignment (same proxy per account always)
    - Automatic rotation on failure
    - Rate limiting per proxy (don't overload one proxy with many accounts)
    """

    def __init__(self, redis_client: redis.Redis, db_session):
        self._redis = redis_client
        self._db = db_session

    async def get_proxy_for_account(self, account: Account) -> Proxy | None:
        """Return the sticky proxy for this account, or assign a new one."""
        if account.proxy_id:
            proxy = await self._db.get(Proxy, account.proxy_id)
            if proxy and proxy.is_healthy:
                return proxy
            # Proxy unhealthy — reassign
        return await self._assign_best_proxy(account)

    async def _assign_best_proxy(self, account: Account) -> Proxy | None:
        """
        Pick the best available proxy for this account:
        - Healthy proxies only
        - Same country as previous proxy if possible
        - Not overloaded (max 3 accounts per proxy)
        - Prefer mobile for IG/TikTok
        """
        platform = account.platform.slug
        mobile_preferred = platform in ("instagram", "tiktok", "threads")

        query = (
            select(Proxy)
            .where(Proxy.is_healthy == True)
            .order_by(Proxy.failure_count.asc())
        )
        if mobile_preferred:
            # Prefer mobile proxies
            query = query.order_by(
                case((Proxy.provider == "mobile", 0), else_=1),
                Proxy.failure_count.asc()
            )

        proxies = await self._db.execute(query)
        for proxy in proxies.scalars():
            # Check load (max 3 accounts per proxy)
            load = await self._get_proxy_load(proxy.id)
            if load < 3:
                account.proxy_id = proxy.id
                await self._db.commit()
                return proxy
        return None

    async def mark_proxy_failed(self, proxy_id: str, reason: str):
        proxy = await self._db.get(Proxy, proxy_id)
        proxy.failure_count += 1
        if proxy.failure_count >= 5:
            proxy.is_healthy = False
        await self._db.commit()

        # Log for monitoring
        await self._redis.incr(f"sm:proxy:failures:{proxy_id}:{today()}")

    async def health_check_all(self):
        """Run periodically via Celery beat to validate proxy pool."""
        proxies = await self._db.execute(select(Proxy))
        for proxy in proxies.scalars():
            is_ok = await self._check_proxy_health(proxy)
            proxy.is_healthy = is_ok
            proxy.last_checked_at = datetime.now(UTC)
            if is_ok:
                proxy.failure_count = 0
        await self._db.commit()

    async def _check_proxy_health(self, proxy: Proxy) -> bool:
        try:
            async with httpx.AsyncClient(proxy=proxy.as_httpx_url(), timeout=10) as client:
                resp = await client.get("https://api.ipify.org?format=json")
                return resp.status_code == 200
        except Exception:
            return False
```

---

## 2. Browser Fingerprint Spoofing

Browser fingerprinting is a major detection vector. Platforms run JavaScript that collects dozens of signals and uses them to identify returning visitors and detect automation tools.

### Signals We Patch

```python
# socialmind/stealth/fingerprint.py
from playwright_stealth import stealth_async
import random

FINGERPRINT_PATCHES = {
    # Core automation detection
    "navigator.webdriver": False,         # Remove the smoking gun
    "navigator.plugins": generate_realistic_plugins(),
    "navigator.languages": ["en-US", "en"],
    "navigator.hardwareConcurrency": random.choice([4, 8, 16]),
    "navigator.deviceMemory": random.choice([4, 8]),

    # Canvas fingerprint — randomize slightly to avoid exact match detection
    "canvas_noise": True,                 # Add ±1 pixel noise to canvas operations

    # WebGL — spoof GPU info
    "webgl_vendor": "Intel Inc.",
    "webgl_renderer": random.choice([
        "Intel Iris OpenGL Engine",
        "ANGLE (Intel, Intel(R) UHD Graphics Direct3D11)",
        "Mesa Intel(R) UHD Graphics 620",
    ]),

    # Audio fingerprint
    "audio_noise": True,                  # Tiny noise added to AudioContext output

    # Screen
    "screen_width": random.choice([1366, 1440, 1920, 2560]),
    "screen_height": random.choice([768, 900, 1080, 1440]),
    "color_depth": 24,
    "pixel_ratio": random.choice([1, 1.5, 2]),

    # Timezone
    "timezone": "America/New_York",       # Set per account, consistent

    # Chrome-specific APIs that headless mode lacks
    "chrome_runtime": True,               # Add window.chrome
    "permissions_query": True,            # Patch permissions API
}

class FingerprintProfile:
    """A consistent fingerprint profile assigned to an account."""

    @staticmethod
    def generate(account_id: str) -> dict:
        """Generate a deterministic but realistic fingerprint for an account."""
        rng = random.Random(account_id)  # Seeded: same account → same fingerprint
        return {
            "user_agent": FingerprintProfile._pick_ua(rng),
            "viewport": rng.choice([
                {"width": 390, "height": 844},   # iPhone 14
                {"width": 412, "height": 915},   # Pixel 7
                {"width": 393, "height": 852},   # iPhone 15
            ]),
            "hardware_concurrency": rng.choice([6, 8]),
            "device_memory": rng.choice([4, 8]),
            "webgl_renderer": rng.choice([
                "Adreno (TM) 730",
                "Apple GPU",
                "Mali-G78",
            ]),
            "timezone": rng.choice([
                "America/New_York", "America/Los_Angeles",
                "America/Chicago", "America/Denver",
            ]),
            "screen": rng.choice([
                {"width": 390, "height": 844, "dpr": 3},
                {"width": 412, "height": 915, "dpr": 2.625},
            ]),
        }

    @staticmethod
    def _pick_ua(rng: random.Random) -> str:
        """Pick a real, high-frequency user agent string."""
        UAS = [
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        ]
        return rng.choice(UAS)


async def apply_stealth(page, fingerprint: dict):
    """Apply all stealth patches to a Playwright page."""
    await stealth_async(page)  # playwright-stealth base patches
    await page.set_extra_http_headers({
        "Accept-Language": "en-US,en;q=0.9",
        "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
    })
    await page.set_viewport_size(fingerprint["viewport"])
    # Inject JS to override remaining fingerprint signals
    await page.add_init_script(f"""
        Object.defineProperty(navigator, 'hardwareConcurrency', {{
            get: () => {fingerprint['hardware_concurrency']}
        }});
        Object.defineProperty(navigator, 'deviceMemory', {{
            get: () => {fingerprint['device_memory']}
        }});
    """)
```

### Browser Context Factory

Each account gets its own isolated `BrowserContext` with its own cookies, localStorage, and fingerprint. Contexts are reused across tasks for the same account.

```python
# socialmind/stealth/session.py
from playwright.async_api import async_playwright, BrowserContext

_context_cache: dict[str, BrowserContext] = {}  # account_id → context

class BrowserContextFactory:

    @staticmethod
    async def get_or_create(account: Account, proxy: Proxy | None) -> BrowserContext:
        account_id = account.id
        if account_id in _context_cache:
            ctx = _context_cache[account_id]
            if not ctx.is_closed():
                return ctx

        fingerprint = FingerprintProfile.generate(account_id)
        browser = await get_shared_browser()  # One browser, multiple contexts

        proxy_config = None
        if proxy:
            proxy_config = {
                "server": proxy.as_url(),
                "username": proxy.username,
                "password": proxy.password_decrypted,
            }

        ctx = await browser.new_context(
            user_agent=fingerprint["user_agent"],
            viewport=fingerprint["viewport"],
            device_scale_factor=fingerprint["screen"]["dpr"],
            locale="en-US",
            timezone_id=fingerprint["timezone"],
            proxy=proxy_config,
            storage_state=account.session.browser_storage_state or None,
        )

        # Apply stealth to every new page created in this context
        ctx.on("page", lambda page: asyncio.ensure_future(apply_stealth(page, fingerprint)))

        _context_cache[account_id] = ctx
        return ctx

    @staticmethod
    async def save_state(account: Account):
        """Persist browser cookies and storage to DB after each session."""
        ctx = _context_cache.get(account.id)
        if ctx:
            state = await ctx.storage_state()
            account.session.cookies = state["cookies"]
            account.session.local_storage = state["origins"]
```

---

## 3. Human-Like Timing Engine

Bots are detectable by their mechanical timing. Every automation action gets wrapped in a delay drawn from a distribution that matches measured human behavior.

```python
# socialmind/stealth/timing.py
import asyncio
import random
import math

class TimingEngine:
    """
    Generates human-like delays using parameterized distributions.
    All values are in seconds.
    """

    # (mean, std_dev) tuples for each action type
    DELAY_PROFILES = {
        "post":          (8.0,  3.0),   # Think before posting
        "comment":       (5.0,  2.5),   # Read → think → type
        "like":          (0.8,  0.4),   # Quick tap
        "follow":        (1.5,  0.7),   # Brief profile glance
        "dm":            (12.0, 5.0),   # Compose reply thoughtfully
        "typing":        (0.1,  0.03),  # Per-character delay
        "scroll":        (2.5,  1.0),   # Between scroll events
        "click":         (0.4,  0.2),   # Human click lag
        "form_fill":     (3.0,  1.5),   # Filling out a form
        "form_submit":   (1.5,  0.8),   # Pause before submit
        "page_load":     (1.5,  0.5),   # Wait after navigation
        "session_start": (30.0, 15.0),  # Warm-up time after login
    }

    @classmethod
    async def delay(cls, action_type: str, multiplier: float = 1.0):
        """Apply a human-like delay for the given action type."""
        mean, std = cls.DELAY_PROFILES.get(action_type, (2.0, 1.0))
        mean *= multiplier
        # Use a log-normal distribution (always positive, right-skewed like humans)
        sigma = math.sqrt(math.log(1 + (std / mean) ** 2))
        mu = math.log(mean) - sigma ** 2 / 2
        delay = random.lognormvariate(mu, sigma)
        # Clamp to reasonable bounds
        delay = max(0.1, min(delay, mean * 4))
        await asyncio.sleep(delay)

    @classmethod
    async def type_text(cls, page, selector: str, text: str):
        """Type text with per-character human delays, including occasional mistakes."""
        element = page.locator(selector)
        for char in text:
            # Occasionally add a typo and correct it
            if random.random() < 0.02:  # 2% typo rate
                wrong_char = random.choice("qwertyuiopasdfghjklzxcvbnm")
                await element.press(wrong_char)
                await asyncio.sleep(random.uniform(0.1, 0.4))
                await element.press("Backspace")
                await asyncio.sleep(random.uniform(0.05, 0.2))
            await element.type(char, delay=random.lognormvariate(-2.3, 0.5) * 1000)

    @classmethod
    async def human_scroll(cls, page, scroll_count: int = 3):
        """Scroll through a feed in a human-like pattern."""
        for _ in range(scroll_count):
            scroll_amount = random.randint(300, 800)
            await page.mouse.wheel(0, scroll_amount)
            await cls.delay("scroll")
            # Occasionally scroll back up slightly
            if random.random() < 0.2:
                await page.mouse.wheel(0, -random.randint(50, 200))
                await asyncio.sleep(random.uniform(0.3, 0.8))
```

---

## 4. Account Warmup Protocol

New accounts must be warmed up gradually. Sudden high activity on a fresh account is a strong bot signal.

```python
# Warmup schedule: days → max daily actions
WARMUP_SCHEDULE = {
    1:  {"likes": 5,  "follows": 3,  "comments": 0, "posts": 0},
    2:  {"likes": 10, "follows": 5,  "comments": 2, "posts": 0},
    3:  {"likes": 15, "follows": 8,  "comments": 3, "posts": 1},
    5:  {"likes": 25, "follows": 12, "comments": 5, "posts": 1},
    7:  {"likes": 40, "follows": 15, "comments": 8, "posts": 2},
    14: {"likes": 60, "follows": 20, "comments": 12, "posts": 3},
    21: {"likes": 80, "follows": 25, "comments": 15, "posts": 4},
    30: {"likes": 100, "follows": 30, "comments": 20, "posts": 5},
}
```

Activities during warmup should look organic:
- Browse feed without taking action
- Like a few posts organically
- Follow accounts in the niche
- Leave occasional genuine-looking comments
- Post 1–2 pieces of content by day 3+

---

## 5. Rate Limiting

Per-account rate limits are enforced in Redis to prevent over-activity in any time window.

```python
# socialmind/stealth/rate_limiter.py
class AccountRateLimiter:

    LIMITS = {
        # (hourly_max, daily_max)
        "instagram": {
            "likes":    (60,  500),
            "follows":  (60,  200),
            "comments": (30,  150),
            "posts":    (3,   10),
            "dms":      (20,  80),
        },
        "twitter": {
            "likes":    (100, 1000),
            "follows":  (100, 400),
            "posts":    (50,  300),
            "dms":      (50,  200),
        },
        # ... etc per platform
    }

    async def check_and_increment(
        self,
        account_id: str,
        platform: str,
        action: str,
    ) -> bool:
        """Returns True if action is allowed, False if rate limited."""
        hourly_max, daily_max = self.LIMITS[platform][action]

        hourly_key = f"sm:rl:{account_id}:{action}:{hour_bucket()}"
        daily_key = f"sm:rl:{account_id}:{action}:{day_bucket()}"

        pipe = self._redis.pipeline()
        pipe.incr(hourly_key)
        pipe.expire(hourly_key, 3600)
        pipe.incr(daily_key)
        pipe.expire(daily_key, 86400)
        hourly_count, _, daily_count, _ = await pipe.execute()

        if hourly_count > hourly_max or daily_count > daily_max:
            return False
        return True
```

---

## 6. CAPTCHA Handling

CAPTCHAs will occasionally appear. The strategy:

1. **Avoid triggering them** — Good stealth + slow warmup prevents most CAPTCHAs
2. **Solve automatically** — Integrate a CAPTCHA solving service for unavoidable cases
3. **Mark account + pause** — If CAPTCHAs persist, pause the account and alert

```python
# Supported CAPTCHA solvers (configure via env var CAPTCHA_SOLVER)
CAPTCHA_SOLVERS = {
    "2captcha": TwoCaptchaSolver,      # API key: CAPTCHA_API_KEY
    "anticaptcha": AntiCaptchaSolver,
    "capsolver": CapsolverSolver,
    "manual": ManualCaptchaSolver,     # Sends to dashboard for human review
}
```

---

## 7. Detection Response Protocol

When a detection event is identified (HTTP 429, checkpoint pages, login challenges):

```
Level 1 — Soft detection (rate limited):
  → Stop current task
  → Wait 15–60 minutes (random)
  → Resume with reduced action frequency

Level 2 — Hard detection (checkpoint / CAPTCHA):
  → Stop all tasks for account
  → Attempt CAPTCHA solve
  → If solved: resume after 2-hour cool-down
  → If not solved: pause account, alert dashboard

Level 3 — Account action (temporary ban):
  → Suspend account in DB
  → Alert user via dashboard
  → Do NOT attempt to login for 24–72 hours
  → Reassign proxy

Level 4 — Permanent ban:
  → Mark account as suspended permanently
  → Alert user
  → Archive account's data
```

---

## Stealth Checklist for New Account Setup

- [ ] Assign a mobile/residential proxy (never datacenter for IG/TikTok)
- [ ] Generate and persist a consistent device fingerprint
- [ ] Enable warmup mode (30-day schedule)
- [ ] Set timezone and locale to match proxy geography
- [ ] Vary login times (don't log in at exactly 9:00:00 AM every day)
- [ ] Enable human-like typing for all text input
- [ ] Set a realistic `daily_action_limit` for the warmup phase
- [ ] Configure persona to generate varied, non-repetitive content
