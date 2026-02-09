"""
Shared utility functions for advanced data preparation.

Pure helper functions for common operations across modules.
"""

from decimal import Decimal
from typing import Any


def safe_divide(numerator: Decimal, denominator: Decimal, default: Decimal = Decimal(0)) -> Decimal:
    """
    Safely divide, returning default if denominator is zero.

    Args:
        numerator: Numerator.
        denominator: Denominator.
        default: Value to return if denominator is zero.

    Returns:
        Division result or default.
    """
    if denominator == 0:
        return default
    return numerator / denominator


def clamp(value: Decimal, min_val: Decimal, max_val: Decimal) -> Decimal:
    """
    Clamp value to range [min_val, max_val].

    Args:
        value: Value to clamp.
        min_val: Minimum value.
        max_val: Maximum value.

    Returns:
        Clamped value.
    """
    return max(min_val, min(value, max_val))


def round_to_precision(value: Decimal, precision: int) -> Decimal:
    """
    Round Decimal to specified precision.

    Args:
        value: Value to round.
        precision: Number of decimal places.

    Returns:
        Rounded value.
    """
    quantizer = Decimal(10) ** -precision
    return value.quantize(quantizer)


def is_close(a: Decimal, b: Decimal, tolerance: Decimal = Decimal("0.0001")) -> bool:
    """
    Check if two Decimals are approximately equal.

    Args:
        a: First value.
        b: Second value.
        tolerance: Absolute tolerance.

    Returns:
        True if |a - b| <= tolerance.
    """
    return abs(a - b) <= tolerance


def validate_positive(value: Any, name: str) -> None:
    """
    Validate that value is positive.

    Args:
        value: Value to check.
        name: Parameter name for error message.

    Raises:
        ValueError: If value is not positive.
    """
    if not isinstance(value, (int, float, Decimal)) or value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")


def validate_non_negative(value: Any, name: str) -> None:
    """
    Validate that value is non-negative.

    Args:
        value: Value to check.
        name: Parameter name for error message.

    Raises:
        ValueError: If value is negative.
    """
    if not isinstance(value, (int, float, Decimal)) or value < 0:
        raise ValueError(f"{name} must be non-negative, got {value}")


def format_decimal(value: Decimal, decimals: int = 8) -> str:
    """
    Format Decimal for display.

    Args:
        value: Decimal value.
        decimals: Number of decimal places.

    Returns:
        Formatted string.
    """
    return f"{value:.{decimals}f}"


def timestamp_to_candle_open(timestamp_ms: int, timeframe_ms: int) -> int:
    """
    Convert timestamp to candle open time.

    Args:
        timestamp_ms: Timestamp in milliseconds.
        timeframe_ms: Timeframe in milliseconds.

    Returns:
        Candle open timestamp (floor to timeframe boundary).
    """
    return (timestamp_ms // timeframe_ms) * timeframe_ms


def timestamps_aligned(timestamps: list[int], timeframe_ms: int) -> bool:
    """
    Check if all timestamps are aligned to timeframe boundaries.

    Args:
        timestamps: List of timestamps in milliseconds.
        timeframe_ms: Timeframe in milliseconds.

    Returns:
        True if all timestamps are aligned.
    """
    return all(ts % timeframe_ms == 0 for ts in timestamps)


def batch_to_chunks(items: list[Any], chunk_size: int) -> list[list[Any]]:
    """
    Split list into chunks of specified size.

    Args:
        items: List of items.
        chunk_size: Size of each chunk.

    Returns:
        List of chunks.
    """
    if chunk_size <= 0:
        raise ValueError(f"Chunk size must be positive, got {chunk_size}")

    return [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]
