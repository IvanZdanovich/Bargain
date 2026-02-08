"""Pure functions for data normalization and validation.

This module contains pure functions with no side effects for:
- Type conversion (strings to Decimal, etc.)
- Symbol normalization across providers
- Side normalization (buy/sell)
- Timestamp validation
- Sequence gap detection
"""

from decimal import Decimal, InvalidOperation
from typing import Any

from src.types import Side
from src.config import get_normalization_config, get_validation_config


def to_decimal(value: Any) -> Decimal:
    """
    Safely convert value to Decimal.

    Args:
        value: Numeric value (str, int, float).

    Returns:
        Decimal representation.

    Raises:
        ValueError: If conversion fails.
    """
    try:
        return Decimal(str(value))
    except InvalidOperation as e:
        raise ValueError(f"Cannot convert {value!r} to Decimal") from e


def normalize_side(raw_side: str) -> Side:
    """
    Normalize trade side to standard format.

    Args:
        raw_side: Provider-specific side string.

    Returns:
        Normalized 'buy' or 'sell'.

    Raises:
        ValueError: If side cannot be determined.
    """
    lowered = raw_side.lower().strip()
    if lowered in ("buy", "bid", "b", "long", "buyer"):
        return "buy"
    if lowered in ("sell", "ask", "s", "short", "seller"):
        return "sell"
    raise ValueError(f"Unknown side: {raw_side}")


def normalize_symbol(symbol: str, provider: str) -> str:
    """
    Normalize symbol to unified format (BASE/QUOTE).

    Args:
        symbol: Provider-specific symbol.
        provider: Provider name for format detection.

    Returns:
        Normalized symbol like 'BTC/USDT'.
    """
    # Remove common separators and normalize to uppercase
    clean = symbol.upper().replace("-", "").replace("_", "").replace("/", "")

    # Get quote currencies from config
    norm_config = get_normalization_config()
    quotes = norm_config["quote_currencies"]

    for quote in quotes:
        if clean.endswith(quote):
            base = clean[: -len(quote)]
            if base:  # Ensure we have a base currency
                return f"{base}/{quote}"

    # Return as-is if pattern not recognized
    return symbol.upper()


def denormalize_symbol(symbol: str, provider: str) -> str:
    """
    Convert normalized symbol back to provider format.

    Args:
        symbol: Normalized symbol like 'BTC/USDT'.
        provider: Target provider name.

    Returns:
        Provider-specific symbol format.
    """
    if provider == "binance":
        return symbol.replace("/", "").upper()
    # Add more providers as needed
    return symbol.replace("/", "")


def validate_timestamp(timestamp_ms: int) -> bool:
    """
    Validate timestamp is within reasonable bounds.

    Args:
        timestamp_ms: Unix timestamp in milliseconds.

    Returns:
        True if valid, False otherwise.
    """
    validation_config = get_validation_config()
    min_ts = validation_config["min_timestamp_ms"]
    max_ts = validation_config["max_timestamp_ms"]
    return min_ts <= timestamp_ms <= max_ts


def validate_sequence(
    current_seq: int,
    last_seq: int | None,
) -> tuple[bool, int | None]:
    """
    Validate sequence continuity, detect gaps.

    Args:
        current_seq: Current message sequence number.
        last_seq: Last processed sequence number.

    Returns:
        Tuple of (is_valid, gap_size or None).
        - (True, None) for valid sequence
        - (False, gap_size) for gap detected
        - (False, None) for duplicate/out-of-order
    """
    if last_seq is None:
        return True, None

    expected = last_seq + 1
    if current_seq == expected:
        return True, None
    if current_seq > expected:
        return False, current_seq - expected
    # Duplicate or out-of-order
    return False, None


def validate_price(price: Decimal) -> bool:
    """
    Validate price is positive and reasonable.

    Args:
        price: Price value.

    Returns:
        True if valid.
    """
    return price > 0


def validate_quantity(quantity: Decimal) -> bool:
    """
    Validate quantity is positive.

    Args:
        quantity: Quantity value.

    Returns:
        True if valid.
    """
    return quantity > 0


def validate_orderbook_integrity(
    bids: list[tuple[Decimal, Decimal]],
    asks: list[tuple[Decimal, Decimal]],
) -> tuple[bool, str | None]:
    """
    Validate order book integrity.

    Args:
        bids: List of (price, quantity) tuples.
        asks: List of (price, quantity) tuples.

    Returns:
        Tuple of (is_valid, error_message or None).
    """
    if not bids or not asks:
        return True, None  # Empty book is valid

    best_bid = bids[0][0]
    best_ask = asks[0][0]

    if best_bid >= best_ask:
        return False, f"Crossed book: bid {best_bid} >= ask {best_ask}"

    # Validate bid ordering (descending)
    for i in range(1, len(bids)):
        if bids[i][0] >= bids[i - 1][0]:
            return False, f"Bids not sorted descending at index {i}"

    # Validate ask ordering (ascending)
    for i in range(1, len(asks)):
        if asks[i][0] <= asks[i - 1][0]:
            return False, f"Asks not sorted ascending at index {i}"

    return True, None


def get_current_timestamp_ms() -> int:
    """
    Get current Unix timestamp in milliseconds.

    Returns:
        Current timestamp in milliseconds.
    """
    import time

    return int(time.time() * 1000)

