"""
Pure transform functions for candle and price data.

Includes Heiken Ashi, returns, normalization, and other stateless transforms.
"""

from decimal import Decimal

from src.types import HeikenAshiData, ResampledCandleData


def compute_heiken_ashi(
    current_candle: ResampledCandleData, prev_ha: HeikenAshiData | None
) -> HeikenAshiData:
    """
    Compute Heiken Ashi candle from regular candle.

    Args:
        current_candle: Current OHLC candle.
        prev_ha: Previous Heiken Ashi candle (None for first candle).

    Returns:
        Heiken Ashi candle.
    """
    open_price = current_candle["open"]
    high = current_candle["high"]
    low = current_candle["low"]
    close = current_candle["close"]

    # HA Close = (O + H + L + C) / 4
    ha_close = (open_price + high + low + close) / 4

    # HA Open = (prev_HA_open + prev_HA_close) / 2
    if prev_ha is None:
        ha_open = (open_price + close) / 2
    else:
        ha_open = (prev_ha["ha_open"] + prev_ha["ha_close"]) / 2

    # HA High = max(H, HA_open, HA_close)
    ha_high = max(high, ha_open, ha_close)

    # HA Low = min(L, HA_open, HA_close)
    ha_low = min(low, ha_open, ha_close)

    return {
        "open_time_ms": current_candle["open_time_ms"],
        "close_time_ms": current_candle["close_time_ms"],
        "ha_open": ha_open,
        "ha_high": ha_high,
        "ha_low": ha_low,
        "ha_close": ha_close,
    }


def compute_log_returns_series(prices: list[Decimal]) -> list[Decimal]:
    """
    Compute log returns from price series.

    Args:
        prices: Price series.

    Returns:
        Log returns (length = len(prices) - 1).
    """
    if len(prices) < 2:
        return []

    returns: list[Decimal] = []
    for i in range(1, len(prices)):
        if prices[i - 1] == 0 or prices[i] == 0:
            returns.append(Decimal(0))
        else:
            returns.append((prices[i] / prices[i - 1]).ln())

    return returns


def compute_percentage_returns_series(prices: list[Decimal]) -> list[Decimal]:
    """
    Compute percentage returns from price series.

    Args:
        prices: Price series.

    Returns:
        Percentage returns (length = len(prices) - 1).
    """
    if len(prices) < 2:
        return []

    returns: list[Decimal] = []
    for i in range(1, len(prices)):
        if prices[i - 1] == 0:
            returns.append(Decimal(0))
        else:
            returns.append(((prices[i] - prices[i - 1]) / prices[i - 1]) * 100)

    return returns


def normalize_min_max(value: Decimal, min_val: Decimal, max_val: Decimal) -> Decimal:
    """
    Normalize value to [0, 1] range using min-max scaling.

    Args:
        value: Value to normalize.
        min_val: Minimum value in range.
        max_val: Maximum value in range.

    Returns:
        Normalized value in [0, 1], or 0 if range is 0.
    """
    if max_val == min_val:
        return Decimal(0)
    return (value - min_val) / (max_val - min_val)


def normalize_z_score(value: Decimal, mean: Decimal, std: Decimal) -> Decimal:
    """
    Normalize value using z-score standardization.

    Args:
        value: Value to normalize.
        mean: Mean of distribution.
        std: Standard deviation.

    Returns:
        Z-score, or 0 if std is 0.
    """
    if std == 0:
        return Decimal(0)
    return (value - mean) / std


def compute_typical_price(high: Decimal, low: Decimal, close: Decimal) -> Decimal:
    """
    Compute typical price (HLC/3).

    Args:
        high: High price.
        low: Low price.
        close: Close price.

    Returns:
        Typical price.
    """
    return (high + low + close) / 3


def compute_pivot_point(high: Decimal, low: Decimal, close: Decimal) -> Decimal:
    """
    Compute pivot point (standard formula).

    Args:
        high: Previous day high.
        low: Previous day low.
        close: Previous day close.

    Returns:
        Pivot point.
    """
    return (high + low + close) / 3


def compute_support_resistance(
    pivot: Decimal, high: Decimal, low: Decimal
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """
    Compute support and resistance levels from pivot.

    Args:
        pivot: Pivot point.
        high: Previous day high.
        low: Previous day low.

    Returns:
        Tuple of (R1, R2, S1, S2).
    """
    r1 = 2 * pivot - low
    s1 = 2 * pivot - high
    r2 = pivot + (high - low)
    s2 = pivot - (high - low)
    return (r1, r2, s1, s2)


def is_bullish_candle(candle: ResampledCandleData) -> bool:
    """
    Check if candle is bullish (close > open).

    Args:
        candle: OHLC candle.

    Returns:
        True if bullish.
    """
    return candle["close"] > candle["open"]


def is_bearish_candle(candle: ResampledCandleData) -> bool:
    """
    Check if candle is bearish (close < open).

    Args:
        candle: OHLC candle.

    Returns:
        True if bearish.
    """
    return candle["close"] < candle["open"]


def compute_candle_body_size(candle: ResampledCandleData) -> Decimal:
    """
    Compute candle body size (absolute difference between open and close).

    Args:
        candle: OHLC candle.

    Returns:
        Body size.
    """
    return abs(candle["close"] - candle["open"])


def compute_candle_wick_sizes(candle: ResampledCandleData) -> tuple[Decimal, Decimal]:
    """
    Compute upper and lower wick sizes.

    Args:
        candle: OHLC candle.

    Returns:
        Tuple of (upper_wick, lower_wick).
    """
    body_high = max(candle["open"], candle["close"])
    body_low = min(candle["open"], candle["close"])

    upper_wick = candle["high"] - body_high
    lower_wick = body_low - candle["low"]

    return (upper_wick, lower_wick)


def compute_candle_range(candle: ResampledCandleData) -> Decimal:
    """
    Compute candle range (high - low).

    Args:
        candle: OHLC candle.

    Returns:
        Candle range.
    """
    return candle["high"] - candle["low"]

