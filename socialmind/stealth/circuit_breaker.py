from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from enum import Enum
from typing import Callable


class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation — requests pass through
    OPEN = "open"          # Failing — requests are rejected immediately
    HALF_OPEN = "half_open"  # Testing recovery — one probe request allowed


class CircuitBreakerOpenError(Exception):
    """Raised when the circuit breaker is open and the call is rejected."""


class CircuitBreaker:
    """
    3-state circuit breaker for protecting adapter operations.

    State transitions:
    - CLOSED → OPEN: when failure_threshold consecutive failures occur
    - OPEN → HALF_OPEN: after recovery_timeout seconds
    - HALF_OPEN → CLOSED: if the probe request succeeds
    - HALF_OPEN → OPEN: if the probe request fails
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 2,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: datetime | None = None
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    async def call(self, func: Callable, *args, **kwargs):
        """
        Execute the callable through the circuit breaker.

        Raises CircuitBreakerOpenError if the circuit is open.
        """
        async with self._lock:
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._state = CircuitState.HALF_OPEN
                    self._success_count = 0
                else:
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker '{self.name}' is OPEN. "
                        "Call rejected to protect downstream service."
                    )

        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as exc:
            await self._on_failure()
            raise exc

    async def _on_success(self) -> None:
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0

    async def _on_failure(self) -> None:
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.now(timezone.utc)

            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
            elif self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN

    def _should_attempt_reset(self) -> bool:
        if self._last_failure_time is None:
            return True
        elapsed = (datetime.now(timezone.utc) - self._last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout

    def reset(self) -> None:
        """Manually reset the circuit breaker to CLOSED state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None

    def __repr__(self) -> str:
        return (
            f"CircuitBreaker(name={self.name!r}, state={self._state.value}, "
            f"failures={self._failure_count})"
        )


# Per-account circuit breaker registry
_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(key: str, **kwargs) -> CircuitBreaker:
    """Get or create a named circuit breaker."""
    if key not in _breakers:
        _breakers[key] = CircuitBreaker(name=key, **kwargs)
    return _breakers[key]
