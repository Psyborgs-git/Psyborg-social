from __future__ import annotations

import asyncio
import pytest
from socialmind.stealth.timing import TimingEngine


@pytest.mark.asyncio
async def test_delay_profiles_defined():
    expected_actions = {"post", "comment", "like", "follow", "dm", "click", "scroll"}
    for action in expected_actions:
        assert action in TimingEngine.DELAY_PROFILES, f"Missing profile for {action}"


@pytest.mark.asyncio
async def test_delay_returns_reasonable_value():
    slept = []
    original_sleep = asyncio.sleep

    async def mock_sleep(seconds):
        slept.append(seconds)

    asyncio.sleep = mock_sleep
    try:
        await TimingEngine.delay("click")
        assert len(slept) == 1
        assert slept[0] > 0
    finally:
        asyncio.sleep = original_sleep


def test_delay_profile_values_are_positive():
    for action, (mean, std) in TimingEngine.DELAY_PROFILES.items():
        assert mean > 0, f"Mean for {action} should be positive"
        assert std > 0, f"Std for {action} should be positive"


@pytest.mark.asyncio
async def test_delay_multiplier():
    slept = []
    original_sleep = asyncio.sleep

    async def mock_sleep(seconds):
        slept.append(seconds)

    asyncio.sleep = mock_sleep
    try:
        await TimingEngine.delay("like", multiplier=1.0)
        base_delay = slept[-1]

        await TimingEngine.delay("like", multiplier=3.0)
        scaled_delay = slept[-1]

        assert base_delay > 0
        assert scaled_delay > 0
    finally:
        asyncio.sleep = original_sleep
