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


# === Advanced Candle Patterns ===


def is_doji(candle: ResampledCandleData, threshold: Decimal = Decimal("0.1")) -> bool:
    """
    Detect Doji pattern (open ≈ close).

    Args:
        candle: OHLC candle.
        threshold: Maximum body/range ratio for Doji (default 0.1 = 10%).

    Returns:
        True if Doji pattern detected.
    """
    body_size = compute_candle_body_size(candle)
    range_size = compute_candle_range(candle)

    if range_size == 0:
        return True

    return (body_size / range_size) <= threshold


def is_hammer(
    candle: ResampledCandleData,
    trend: str = "down",
    body_ratio_threshold: Decimal = Decimal("0.3"),
    lower_wick_ratio: Decimal = Decimal("2.0"),
) -> bool:
    """
    Detect Hammer pattern (bullish reversal).

    Args:
        candle: OHLC candle.
        trend: Prior trend ("down" for hammer, "up" for inverted hammer).
        body_ratio_threshold: Max body size / range ratio (default 30%).
        lower_wick_ratio: Min lower wick / body ratio (default 2x).

    Returns:
        True if Hammer pattern detected.
    """
    body_size = compute_candle_body_size(candle)
    range_size = compute_candle_range(candle)
    upper_wick, lower_wick = compute_candle_wick_sizes(candle)

    if range_size == 0 or body_size == 0:
        return False

    # Small body relative to range
    if (body_size / range_size) > body_ratio_threshold:
        return False

    # Long lower wick
    if trend == "down":
        return (lower_wick / body_size) >= lower_wick_ratio and upper_wick < body_size
    # inverted hammer
    return (upper_wick / body_size) >= lower_wick_ratio and lower_wick < body_size


def is_shooting_star(
    candle: ResampledCandleData,
    body_ratio_threshold: Decimal = Decimal("0.3"),
    upper_wick_ratio: Decimal = Decimal("2.0"),
) -> bool:
    """
    Detect Shooting Star pattern (bearish reversal).

    Args:
        candle: OHLC candle.
        body_ratio_threshold: Max body size / range ratio (default 30%).
        upper_wick_ratio: Min upper wick / body ratio (default 2x).

    Returns:
        True if Shooting Star detected.
    """
    body_size = compute_candle_body_size(candle)
    range_size = compute_candle_range(candle)
    upper_wick, lower_wick = compute_candle_wick_sizes(candle)

    if range_size == 0 or body_size == 0:
        return False

    # Small body at bottom
    if (body_size / range_size) > body_ratio_threshold:
        return False

    # Long upper wick, small lower wick
    return (upper_wick / body_size) >= upper_wick_ratio and lower_wick < body_size


def is_engulfing_bullish(candle: ResampledCandleData, prev_candle: ResampledCandleData) -> bool:
    """
    Detect Bullish Engulfing pattern.

    Args:
        candle: Current candle (should be bullish).
        prev_candle: Previous candle (should be bearish).

    Returns:
        True if Bullish Engulfing detected.
    """
    # Current must be bullish, previous must be bearish
    if not is_bullish_candle(candle) or not is_bearish_candle(prev_candle):
        return False

    # Current body must engulf previous body
    curr_body_top = candle["close"]
    curr_body_bottom = candle["open"]
    prev_body_top = prev_candle["open"]
    prev_body_bottom = prev_candle["close"]

    return curr_body_bottom <= prev_body_bottom and curr_body_top >= prev_body_top


def is_engulfing_bearish(candle: ResampledCandleData, prev_candle: ResampledCandleData) -> bool:
    """
    Detect Bearish Engulfing pattern.

    Args:
        candle: Current candle (should be bearish).
        prev_candle: Previous candle (should be bullish).

    Returns:
        True if Bearish Engulfing detected.
    """
    # Current must be bearish, previous must be bullish
    if not is_bearish_candle(candle) or not is_bullish_candle(prev_candle):
        return False

    # Current body must engulf previous body
    curr_body_top = candle["open"]
    curr_body_bottom = candle["close"]
    prev_body_top = prev_candle["close"]
    prev_body_bottom = prev_candle["open"]

    return curr_body_bottom <= prev_body_bottom and curr_body_top >= prev_body_top


def is_morning_star(
    candle1: ResampledCandleData,
    candle2: ResampledCandleData,
    candle3: ResampledCandleData,
) -> bool:
    """
    Detect Morning Star pattern (bullish reversal).

    Args:
        candle1: First candle (should be bearish).
        candle2: Second candle (small body - star).
        candle3: Third candle (should be bullish).

    Returns:
        True if Morning Star detected.
    """
    # First must be bearish
    if not is_bearish_candle(candle1):
        return False

    # Second must be small (doji or small body)
    if not is_doji(candle2, threshold=Decimal("0.3")):
        return False

    # Third must be bullish
    if not is_bullish_candle(candle3):
        return False

    # Third should close above midpoint of first
    first_midpoint = (candle1["open"] + candle1["close"]) / 2
    return candle3["close"] > first_midpoint


def is_evening_star(
    candle1: ResampledCandleData,
    candle2: ResampledCandleData,
    candle3: ResampledCandleData,
) -> bool:
    """
    Detect Evening Star pattern (bearish reversal).

    Args:
        candle1: First candle (should be bullish).
        candle2: Second candle (small body - star).
        candle3: Third candle (should be bearish).

    Returns:
        True if Evening Star detected.
    """
    # First must be bullish
    if not is_bullish_candle(candle1):
        return False

    # Second must be small (doji or small body)
    if not is_doji(candle2, threshold=Decimal("0.3")):
        return False

    # Third must be bearish
    if not is_bearish_candle(candle3):
        return False

    # Third should close below midpoint of first
    first_midpoint = (candle1["open"] + candle1["close"]) / 2
    return candle3["close"] < first_midpoint


def is_three_white_soldiers(
    candle1: ResampledCandleData,
    candle2: ResampledCandleData,
    candle3: ResampledCandleData,
) -> bool:
    """
    Detect Three White Soldiers pattern (strong bullish continuation).

    Args:
        candle1: First candle.
        candle2: Second candle.
        candle3: Third candle.

    Returns:
        True if Three White Soldiers detected.
    """
    # All must be bullish
    if not (
        is_bullish_candle(candle1) and is_bullish_candle(candle2) and is_bullish_candle(candle3)
    ):
        return False

    # Each candle should open within previous body
    if not (candle1["close"] >= candle2["open"] >= candle1["open"]):
        return False

    if not (candle2["close"] >= candle3["open"] >= candle2["open"]):
        return False

    # Prices should be ascending
    return candle1["close"] < candle2["close"] < candle3["close"]


def is_three_black_crows(
    candle1: ResampledCandleData,
    candle2: ResampledCandleData,
    candle3: ResampledCandleData,
) -> bool:
    """
    Detect Three Black Crows pattern (strong bearish continuation).

    Args:
        candle1: First candle.
        candle2: Second candle.
        candle3: Third candle.

    Returns:
        True if Three Black Crows detected.
    """
    # All must be bearish
    if not (
        is_bearish_candle(candle1) and is_bearish_candle(candle2) and is_bearish_candle(candle3)
    ):
        return False

    # Each candle should open within previous body
    if not (candle1["close"] <= candle2["open"] <= candle1["open"]):
        return False

    if not (candle2["close"] <= candle3["open"] <= candle2["open"]):
        return False

    # Prices should be descending
    return candle1["close"] > candle2["close"] > candle3["close"]


def detect_candle_pattern(
    candles: list[ResampledCandleData],
) -> list[str]:
    """
    Detect all applicable candle patterns.

    Args:
        candles: List of candles (1-3 candles depending on pattern).

    Returns:
        List of detected pattern names.
    """
    patterns: list[str] = []

    if not candles:
        return patterns

    current = candles[-1]

    # Single candle patterns
    if is_doji(current):
        patterns.append("doji")

    if is_hammer(current, trend="down"):
        patterns.append("hammer")

    if is_hammer(current, trend="up"):
        patterns.append("inverted_hammer")

    if is_shooting_star(current):
        patterns.append("shooting_star")

    # Two candle patterns
    if len(candles) >= 2:
        prev = candles[-2]

        if is_engulfing_bullish(current, prev):
            patterns.append("bullish_engulfing")

        if is_engulfing_bearish(current, prev):
            patterns.append("bearish_engulfing")

    # Three candle patterns
    if len(candles) >= 3:
        candle1 = candles[-3]
        candle2 = candles[-2]
        candle3 = candles[-1]

        if is_morning_star(candle1, candle2, candle3):
            patterns.append("morning_star")

        if is_evening_star(candle1, candle2, candle3):
            patterns.append("evening_star")

        if is_three_white_soldiers(candle1, candle2, candle3):
            patterns.append("three_white_soldiers")

        if is_three_black_crows(candle1, candle2, candle3):
            patterns.append("three_black_crows")

    return patterns
