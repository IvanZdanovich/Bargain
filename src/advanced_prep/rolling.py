"""
Rolling window implementation using ring buffers for O(1) operations.

Provides efficient rolling statistics and window management for streaming data.
"""

from collections import deque
from collections.abc import Sequence
from decimal import Decimal


class RollingWindow:
    """
    Ring buffer-based rolling window with O(1) append and efficient statistics.

    Args:
        size: Window size (number of elements).

    Side effects:
        None (pure data structure).
    """

    def __init__(self, size: int) -> None:
        """Initialize rolling window with specified size."""
        if size <= 0:
            raise ValueError(f"Window size must be positive, got {size}")
        self._size = size
        self._buffer: deque[Decimal] = deque(maxlen=size)
        self._sum = Decimal(0)
        self._sum_squares = Decimal(0)

    def append(self, value: Decimal) -> None:
        """
        Append new value to window, removing oldest if full.

        Args:
            value: Value to append.

        Side effects:
            Updates internal buffer and cached sums.
        """
        # If buffer is full, remove oldest from sums
        if len(self._buffer) == self._size:
            oldest = self._buffer[0]
            self._sum -= oldest
            self._sum_squares -= oldest * oldest

        # Add new value
        self._buffer.append(value)
        self._sum += value
        self._sum_squares += value * value

    def mean(self) -> Decimal:
        """
        Compute rolling mean.

        Returns:
            Mean of values in window, or 0 if empty.
        """
        if not self._buffer:
            return Decimal(0)
        return self._sum / len(self._buffer)

    def std(self) -> Decimal:
        """
        Compute rolling standard deviation.

        Returns:
            Standard deviation of values in window, or 0 if < 2 elements.
        """
        n = len(self._buffer)
        if n < 2:
            return Decimal(0)

        variance = (self._sum_squares / n) - (self._sum / n) ** 2
        # Handle floating point precision issues
        if variance < 0:
            variance = Decimal(0)
        return variance.sqrt()

    def sum(self) -> Decimal:
        """
        Get rolling sum.

        Returns:
            Sum of all values in window.
        """
        return self._sum

    def max(self) -> Decimal | None:
        """
        Get maximum value in window.

        Returns:
            Maximum value, or None if empty.
        """
        return max(self._buffer) if self._buffer else None

    def min(self) -> Decimal | None:
        """
        Get minimum value in window.

        Returns:
            Minimum value, or None if empty.
        """
        return min(self._buffer) if self._buffer else None

    def is_full(self) -> bool:
        """
        Check if window is full.

        Returns:
            True if window contains size elements.
        """
        return len(self._buffer) == self._size

    def size(self) -> int:
        """
        Get window size (capacity).

        Returns:
            Maximum number of elements.
        """
        return self._size

    def count(self) -> int:
        """
        Get current number of elements in window.

        Returns:
            Number of elements currently in window.
        """
        return len(self._buffer)

    def to_list(self) -> list[Decimal]:
        """
        Convert window to list (oldest to newest).

        Returns:
            List of all values in window order.
        """
        return list(self._buffer)

    def reset(self) -> None:
        """
        Clear all values from window.

        Side effects:
            Resets buffer and cached sums.
        """
        self._buffer.clear()
        self._sum = Decimal(0)
        self._sum_squares = Decimal(0)


def compute_rolling_mean(values: Sequence[Decimal], window: int) -> list[Decimal]:
    """
    Compute rolling mean over sequence (batch mode).

    Args:
        values: Input sequence.
        window: Window size.

    Returns:
        List of rolling means (length = len(values) - window + 1).
    """
    if window <= 0 or window > len(values):
        return []

    result: list[Decimal] = []
    window_sum = sum(values[:window])
    result.append(Decimal(window_sum) / Decimal(window))

    for i in range(window, len(values)):
        window_sum = window_sum - values[i - window] + values[i]
        result.append(Decimal(window_sum) / Decimal(window))

    return result


def compute_rolling_std(values: Sequence[Decimal], window: int) -> list[Decimal]:
    """
    Compute rolling standard deviation over sequence (batch mode).

    Args:
        values: Input sequence.
        window: Window size.

    Returns:
        List of rolling standard deviations (length = len(values) - window + 1).
    """
    if window <= 0 or window > len(values):
        return []

    result: list[Decimal] = []
    for i in range(window, len(values) + 1):
        window_values = values[i - window : i]
        mean = Decimal(sum(window_values)) / Decimal(window)
        variance = Decimal(sum((v - mean) ** 2 for v in window_values)) / Decimal(window)
        result.append(variance.sqrt() if variance > 0 else Decimal(0))

    return result


def compute_z_score(value: Decimal, mean: Decimal, std: Decimal) -> Decimal:
    """
    Compute z-score for value given mean and standard deviation.

    Args:
        value: Value to normalize.
        mean: Rolling mean.
        std: Rolling standard deviation.

    Returns:
        Z-score, or 0 if std is 0.
    """
    if std == 0:
        return Decimal(0)
    return (value - mean) / std
