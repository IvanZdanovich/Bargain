"""Error handling, reconnection, and rate limiting utilities.

This module provides:
- Exponential backoff retry logic
- Token bucket rate limiting
- Data integrity validation
- Health monitoring helpers
"""

import asyncio
import logging
from typing import Callable, Awaitable, TypeVar

from src.types import ProviderConfigData, RateLimiterStateData
from src.config import get_reliability_config

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def with_exponential_backoff(
    operation: Callable[[], Awaitable[T]],
    max_attempts: int | None = None,
    base_delay_ms: int | None = None,
    max_delay_ms: int | None = None,
    operation_name: str = "operation",
) -> T:
    """
    Execute operation with exponential backoff retry.

    Args:
        operation: Async function to execute.
        max_attempts: Maximum retry attempts (default from config).
        base_delay_ms: Initial delay in milliseconds (default from config).
        max_delay_ms: Maximum delay cap in milliseconds (default from config).
        operation_name: Name for logging.

    Returns:
        Result of successful operation.

    Raises:
        Exception: If all retries exhausted.
    """
    reliability_cfg = get_reliability_config()

    if max_attempts is None:
        max_attempts = reliability_cfg["max_attempts"]
    if base_delay_ms is None:
        base_delay_ms = reliability_cfg["base_delay_ms"]
    if max_delay_ms is None:
        max_delay_ms = reliability_cfg["max_delay_ms"]

    last_exception: Exception | None = None

    for attempt in range(max_attempts):
        try:
            return await operation()
        except asyncio.CancelledError:
            raise  # Don't retry on cancellation
        except Exception as e:
            last_exception = e
            if attempt == max_attempts - 1:
                logger.error(
                    f"{operation_name} failed after {max_attempts} attempts: {e}"
                )
                raise

            delay_ms = min(base_delay_ms * (2**attempt), max_delay_ms)
            delay_s = delay_ms / 1000
            logger.warning(
                f"{operation_name} failed (attempt {attempt + 1}/{max_attempts}), "
                f"retrying in {delay_s:.1f}s: {e}"
            )
            await asyncio.sleep(delay_s)

    # Should never reach here, but satisfy type checker
    if last_exception:
        raise last_exception
    raise RuntimeError("Unexpected state in retry logic")


async def with_provider_backoff(
    operation: Callable[[], Awaitable[T]],
    config: ProviderConfigData,
    operation_name: str = "operation",
) -> T:
    """
    Execute operation with backoff using provider config.

    Args:
        operation: Async function to execute.
        config: Provider configuration with retry settings.
        operation_name: Name for logging.

    Returns:
        Result of successful operation.
    """
    return await with_exponential_backoff(
        operation=operation,
        max_attempts=config["reconnect_attempts"],
        base_delay_ms=config["reconnect_delay_ms"],
        operation_name=operation_name,
    )


def create_rate_limiter(requests_per_second: int) -> RateLimiterStateData:
    """
    Create token bucket rate limiter state.

    Args:
        requests_per_second: Maximum requests per second.

    Returns:
        Rate limiter state dictionary.
    """
    import time

    return RateLimiterStateData(
        tokens=float(requests_per_second),
        max_tokens=requests_per_second,
        last_refill=time.monotonic(),
        refill_rate=requests_per_second,
    )


async def acquire_rate_limit(limiter: RateLimiterStateData) -> None:
    """
    Acquire a rate limit token, waiting if necessary.

    Args:
        limiter: Rate limiter state (modified in place).

    Side effects: Updates token count, may sleep.
    """
    import time

    now = time.monotonic()
    elapsed = now - limiter["last_refill"]

    # Refill tokens based on elapsed time
    refill = elapsed * limiter["refill_rate"]
    limiter["tokens"] = min(limiter["max_tokens"], limiter["tokens"] + refill)
    limiter["last_refill"] = now

    if limiter["tokens"] >= 1:
        limiter["tokens"] -= 1
    else:
        # Wait for token to become available
        wait_time = (1 - limiter["tokens"]) / limiter["refill_rate"]
        await asyncio.sleep(wait_time)
        limiter["tokens"] = 0
        limiter["last_refill"] = time.monotonic()


def validate_data_integrity(
    data: dict,
    required_fields: list[str],
) -> tuple[bool, list[str]]:
    """
    Validate required fields are present and non-null.

    Args:
        data: Data record to validate.
        required_fields: List of required field names.

    Returns:
        Tuple of (is_valid, list of missing fields).
    """
    missing = [
        field
        for field in required_fields
        if field not in data or data[field] is None
    ]
    return len(missing) == 0, missing


def calculate_latency_ms(send_time_ms: int, receive_time_ms: int) -> float:
    """
    Calculate message latency.

    Args:
        send_time_ms: Message send timestamp.
        receive_time_ms: Message receive timestamp.

    Returns:
        Latency in milliseconds.
    """
    return float(receive_time_ms - send_time_ms)


class CircuitBreaker:
    """
    Circuit breaker for provider connections.

    Tracks failures and opens circuit to prevent cascade failures.
    Not a class for state - uses closure pattern internally.
    """

    def __init__(
        self,
        failure_threshold: int | None = None,
        recovery_timeout_s: float | None = None,
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Failures before opening circuit (default from config).
            recovery_timeout_s: Seconds before attempting recovery (default from config).
        """
        reliability_cfg = get_reliability_config()

        if failure_threshold is None:
            failure_threshold = reliability_cfg["failure_threshold"]
        if recovery_timeout_s is None:
            recovery_timeout_s = reliability_cfg["recovery_timeout_s"]

        self._failure_count = 0
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout_s
        self._last_failure_time: float | None = None
        self._is_open = False

    def record_success(self) -> None:
        """Record successful operation, reset failure count."""
        self._failure_count = 0
        self._is_open = False

    def record_failure(self) -> None:
        """Record failed operation, potentially open circuit."""
        import time

        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        if self._failure_count >= self._failure_threshold:
            self._is_open = True
            logger.warning(
                f"Circuit breaker opened after {self._failure_count} failures"
            )

    def is_available(self) -> bool:
        """
        Check if circuit is closed (operations allowed).

        Returns:
            True if operations should proceed.
        """
        if not self._is_open:
            return True

        # Check if recovery timeout has passed
        import time

        if self._last_failure_time is None:
            return True

        elapsed = time.monotonic() - self._last_failure_time
        if elapsed >= self._recovery_timeout:
            logger.info("Circuit breaker attempting recovery")
            return True

        return False

    def get_state(self) -> str:
        """Get circuit breaker state."""
        if not self._is_open:
            return "closed"
        if self.is_available():
            return "half-open"
        return "open"

