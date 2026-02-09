"""Unit tests for reliability utilities."""

import asyncio
import time

import pytest

from src.data_controller.reliability import (
    CircuitBreaker,
    acquire_rate_limit,
    calculate_latency_ms,
    create_rate_limiter,
    validate_data_integrity,
    with_exponential_backoff,
)


class TestExponentialBackoff:
    """Tests for exponential backoff retry."""

    @pytest.mark.asyncio
    async def test_success_on_first_try(self):
        """Return result on first successful attempt."""
        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await with_exponential_backoff(
            operation,
            max_attempts=3,
            base_delay_ms=10,
        )

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Retry on transient failure."""
        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Transient error")
            return "success"

        result = await with_exponential_backoff(
            operation,
            max_attempts=5,
            base_delay_ms=10,
        )

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_exhaust_retries(self):
        """Raise after exhausting retries."""
        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            raise ValueError("Persistent error")

        with pytest.raises(ValueError, match="Persistent error"):
            await with_exponential_backoff(
                operation,
                max_attempts=3,
                base_delay_ms=10,
            )

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_cancellation_not_retried(self):
        """CancelledError is not retried."""
        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            raise asyncio.CancelledError()

        with pytest.raises(asyncio.CancelledError):
            await with_exponential_backoff(
                operation,
                max_attempts=3,
                base_delay_ms=10,
            )

        assert call_count == 1


class TestRateLimiter:
    """Tests for rate limiter."""

    def test_create_rate_limiter(self):
        """Create rate limiter with correct initial state."""
        limiter = create_rate_limiter(10)

        assert limiter["max_tokens"] == 10
        assert limiter["tokens"] == 10.0
        assert limiter["refill_rate"] == 10

    @pytest.mark.asyncio
    async def test_acquire_without_waiting(self):
        """Acquire token immediately when available."""
        limiter = create_rate_limiter(10)

        start = time.monotonic()
        await acquire_rate_limit(limiter)
        elapsed = time.monotonic() - start

        assert elapsed < 0.1
        assert limiter["tokens"] < 10

    @pytest.mark.asyncio
    async def test_acquire_multiple(self):
        """Acquire multiple tokens."""
        limiter = create_rate_limiter(10)

        for _ in range(5):
            await acquire_rate_limit(limiter)

        assert limiter["tokens"] < 6

    @pytest.mark.asyncio
    async def test_token_refill(self):
        """Tokens refill over time."""
        limiter = create_rate_limiter(10)

        # Exhaust all tokens
        for _ in range(10):
            await acquire_rate_limit(limiter)

        # Wait for refill
        await asyncio.sleep(0.2)

        # Should be able to acquire again
        await acquire_rate_limit(limiter)
        assert limiter["tokens"] >= 0


class TestDataIntegrityValidation:
    """Tests for validate_data_integrity."""

    def test_all_fields_present(self):
        """Valid when all required fields present."""
        data = {"field1": "value1", "field2": 123, "field3": True}
        required = ["field1", "field2", "field3"]

        is_valid, missing = validate_data_integrity(data, required)

        assert is_valid is True
        assert missing == []

    def test_missing_field(self):
        """Invalid when field is missing."""
        data = {"field1": "value1"}
        required = ["field1", "field2"]

        is_valid, missing = validate_data_integrity(data, required)

        assert is_valid is False
        assert "field2" in missing

    def test_null_field(self):
        """Invalid when field is None."""
        data = {"field1": "value1", "field2": None}
        required = ["field1", "field2"]

        is_valid, missing = validate_data_integrity(data, required)

        assert is_valid is False
        assert "field2" in missing

    def test_empty_required_list(self):
        """Valid with no required fields."""
        data = {"anything": "value"}
        required = []

        is_valid, missing = validate_data_integrity(data, required)

        assert is_valid is True


class TestLatencyCalculation:
    """Tests for calculate_latency_ms."""

    def test_calculate_latency(self):
        """Calculate correct latency."""
        send_time = 1000
        receive_time = 1050

        latency = calculate_latency_ms(send_time, receive_time)

        assert latency == 50.0

    def test_zero_latency(self):
        """Handle zero latency."""
        latency = calculate_latency_ms(1000, 1000)
        assert latency == 0.0


class TestCircuitBreaker:
    """Tests for CircuitBreaker."""

    def test_initial_state_closed(self):
        """Circuit starts closed."""
        cb = CircuitBreaker(failure_threshold=3)

        assert cb.is_available() is True
        assert cb.get_state() == "closed"

    def test_opens_after_failures(self):
        """Circuit opens after threshold failures."""
        cb = CircuitBreaker(failure_threshold=3)

        cb.record_failure()
        assert cb.is_available() is True

        cb.record_failure()
        assert cb.is_available() is True

        cb.record_failure()
        assert cb.is_available() is False
        assert cb.get_state() == "open"

    def test_success_resets_count(self):
        """Success resets failure count."""
        cb = CircuitBreaker(failure_threshold=3)

        cb.record_failure()
        cb.record_failure()
        cb.record_success()

        assert cb.is_available() is True

        # Need 3 more failures to trip
        cb.record_failure()
        cb.record_failure()
        assert cb.is_available() is True

    def test_recovery_after_timeout(self):
        """Circuit allows attempt after timeout."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout_s=0.1)

        cb.record_failure()
        assert cb.is_available() is False

        # Wait for recovery timeout
        time.sleep(0.15)

        assert cb.is_available() is True
        assert cb.get_state() == "half-open"
