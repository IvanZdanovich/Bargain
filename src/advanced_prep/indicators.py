"""
Technical indicator computation for batch and streaming modes.

Provides pure functions for indicators (EMA, SMA, ATR, etc.) with stateful
streaming support for hot-loop optimization.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence

from src.advanced_prep.rolling import RollingWindow


@dataclass
class EMAState:
    """State for streaming EMA computation."""

    period: int
    value: Decimal
    alpha: Decimal
    initialized: bool


@dataclass
class ATRState:
    """State for streaming ATR computation."""

    period: int
    value: Decimal
    prev_close: Decimal | None
    tr_window: RollingWindow


@dataclass
class RSIState:
    """State for streaming RSI computation."""

    period: int
    value: Decimal
    prev_close: Decimal | None
    gains: RollingWindow
    losses: RollingWindow
    avg_gain: Decimal
    avg_loss: Decimal


# === Batch Indicator Functions ===


def compute_sma(values: Sequence[Decimal], period: int) -> list[Decimal]:
    """
    Compute Simple Moving Average (batch).

    Args:
        values: Price series.
        period: SMA period.

    Returns:
        SMA values (length = len(values) - period + 1).
    """
    if period <= 0 or period > len(values):
        return []

    result: list[Decimal] = []
    window_sum = sum(values[:period])
    result.append(window_sum / period)

    for i in range(period, len(values)):
        window_sum = window_sum - values[i - period] + values[i]
        result.append(window_sum / period)

    return result


def compute_ema(values: Sequence[Decimal], period: int) -> list[Decimal]:
    """
    Compute Exponential Moving Average (batch).

    Args:
        values: Price series.
        period: EMA period.

    Returns:
        EMA values (same length as input, first period-1 values are partial).
    """
    if not values or period <= 0:
        return []

    alpha = Decimal(2) / (period + 1)
    result: list[Decimal] = []

    # Initialize with first value
    ema = values[0]
    result.append(ema)

    for value in values[1:]:
        ema = alpha * value + (Decimal(1) - alpha) * ema
        result.append(ema)

    return result


def compute_wma(values: Sequence[Decimal], period: int) -> list[Decimal]:
    """
    Compute Weighted Moving Average (batch).

    Args:
        values: Price series.
        period: WMA period.

    Returns:
        WMA values (length = len(values) - period + 1).
    """
    if period <= 0 or period > len(values):
        return []

    weights = [Decimal(i + 1) for i in range(period)]
    weight_sum = sum(weights)

    result: list[Decimal] = []
    for i in range(period - 1, len(values)):
        window = values[i - period + 1 : i + 1]
        wma = sum(w * v for w, v in zip(weights, window)) / weight_sum
        result.append(wma)

    return result


def compute_vwap_batch(
    prices: Sequence[Decimal], volumes: Sequence[Decimal]
) -> list[Decimal]:
    """
    Compute cumulative VWAP (batch).

    Args:
        prices: Price series.
        volumes: Volume series.

    Returns:
        VWAP values (same length as input).
    """
    if len(prices) != len(volumes) or not prices:
        return []

    result: list[Decimal] = []
    cumulative_pv = Decimal(0)
    cumulative_volume = Decimal(0)

    for price, volume in zip(prices, volumes):
        cumulative_pv += price * volume
        cumulative_volume += volume
        vwap = cumulative_pv / cumulative_volume if cumulative_volume > 0 else price
        result.append(vwap)

    return result


def compute_true_range(
    high: Decimal, low: Decimal, prev_close: Decimal | None
) -> Decimal:
    """
    Compute True Range for single candle.

    Args:
        high: Candle high.
        low: Candle low.
        prev_close: Previous candle close.

    Returns:
        True Range value.
    """
    if prev_close is None:
        return high - low

    tr1 = high - low
    tr2 = abs(high - prev_close)
    tr3 = abs(low - prev_close)

    return max(tr1, tr2, tr3)


def compute_atr_batch(
    highs: Sequence[Decimal], lows: Sequence[Decimal], closes: Sequence[Decimal], period: int
) -> list[Decimal]:
    """
    Compute Average True Range (batch).

    Args:
        highs: High prices.
        lows: Low prices.
        closes: Close prices.
        period: ATR period.

    Returns:
        ATR values (length = len(highs) - period).
    """
    if len(highs) != len(lows) or len(highs) != len(closes):
        raise ValueError("Price series must have same length")

    if period <= 0 or period >= len(highs):
        return []

    # Compute true ranges
    true_ranges: list[Decimal] = []
    for i in range(len(highs)):
        prev_close = closes[i - 1] if i > 0 else None
        tr = compute_true_range(highs[i], lows[i], prev_close)
        true_ranges.append(tr)

    # Compute ATR as SMA of true ranges
    return compute_sma(true_ranges, period)


# === Streaming Indicator Functions ===


def init_ema_state(period: int, initial_value: Decimal) -> EMAState:
    """
    Initialize EMA state for streaming.

    Args:
        period: EMA period.
        initial_value: Initial price value.

    Returns:
        EMA state.
    """
    alpha = Decimal(2) / (period + 1)
    return EMAState(period=period, value=initial_value, alpha=alpha, initialized=True)


def update_ema_streaming(state: EMAState, new_value: Decimal) -> EMAState:
    """
    Update EMA state with new value (streaming).

    Args:
        state: Current EMA state.
        new_value: New price.

    Returns:
        Updated EMA state.
    """
    if not state.initialized:
        return EMAState(
            period=state.period,
            value=new_value,
            alpha=state.alpha,
            initialized=True,
        )

    new_ema = state.alpha * new_value + (Decimal(1) - state.alpha) * state.value
    return EMAState(
        period=state.period,
        value=new_ema,
        alpha=state.alpha,
        initialized=True,
    )


def init_atr_state(period: int) -> ATRState:
    """
    Initialize ATR state for streaming.

    Args:
        period: ATR period.

    Returns:
        ATR state.
    """
    return ATRState(
        period=period,
        value=Decimal(0),
        prev_close=None,
        tr_window=RollingWindow(period),
    )


def update_atr_streaming(
    state: ATRState, high: Decimal, low: Decimal, close: Decimal
) -> ATRState:
    """
    Update ATR state with new candle (streaming).

    Args:
        state: Current ATR state.
        high: Candle high.
        low: Candle low.
        close: Candle close.

    Returns:
        Updated ATR state.
    """
    # Compute true range
    tr = compute_true_range(high, low, state.prev_close)

    # Update rolling window
    state.tr_window.append(tr)

    # Compute ATR as mean of true ranges
    atr_value = state.tr_window.mean()

    return ATRState(
        period=state.period,
        value=atr_value,
        prev_close=close,
        tr_window=state.tr_window,
    )


def init_rsi_state(period: int, initial_price: Decimal) -> RSIState:
    """
    Initialize RSI state for streaming.

    Args:
        period: RSI period.
        initial_price: Initial price value.

    Returns:
        RSI state.
    """
    return RSIState(
        period=period,
        value=Decimal("50"),
        prev_close=initial_price,
        gains=RollingWindow(period),
        losses=RollingWindow(period),
        avg_gain=Decimal(0),
        avg_loss=Decimal(0),
    )


def update_rsi_streaming(state: RSIState, new_price: Decimal) -> RSIState:
    """
    Update RSI state with new price (streaming).

    Args:
        state: Current RSI state.
        new_price: New price.

    Returns:
        Updated RSI state.
    """
    if state.prev_close is None:
        return RSIState(
            period=state.period,
            value=Decimal("50"),
            prev_close=new_price,
            gains=state.gains,
            losses=state.losses,
            avg_gain=Decimal(0),
            avg_loss=Decimal(0),
        )

    # Calculate price change
    change = new_price - state.prev_close
    gain = change if change > 0 else Decimal(0)
    loss = abs(change) if change < 0 else Decimal(0)

    # Update rolling windows
    state.gains.append(gain)
    state.losses.append(loss)

    # Calculate RSI
    if not state.gains.is_full():
        # Not enough data yet
        return RSIState(
            period=state.period,
            value=Decimal("50"),
            prev_close=new_price,
            gains=state.gains,
            losses=state.losses,
            avg_gain=Decimal(0),
            avg_loss=Decimal(0),
        )

    # Use Wilder's smoothing method
    avg_gain: Decimal
    avg_loss: Decimal

    if state.avg_gain == 0 and state.avg_loss == 0:
        # First calculation - simple average
        avg_gain = state.gains.mean()
        avg_loss = state.losses.mean()
    else:
        # Subsequent calculations - smoothed
        avg_gain = (state.avg_gain * (state.period - 1) + gain) / state.period
        avg_loss = (state.avg_loss * (state.period - 1) + loss) / state.period

    # Calculate RSI
    if avg_loss == 0:
        rsi_value = Decimal("100")
    else:
        rs = avg_gain / avg_loss
        rsi_value = Decimal("100") - (Decimal("100") / (Decimal("1") + rs))

    return RSIState(
        period=state.period,
        value=rsi_value,
        prev_close=new_price,
        gains=state.gains,
        losses=state.losses,
        avg_gain=avg_gain,
        avg_loss=avg_loss,
    )


# === Volatility Indicators ===


def compute_rolling_volatility(returns: Sequence[Decimal], period: int) -> list[Decimal]:
    """
    Compute rolling volatility (standard deviation of returns).

    Args:
        returns: Return series (e.g., log returns).
        period: Rolling window period.

    Returns:
        Rolling volatility values.
    """
    if period <= 0 or period > len(returns):
        return []

    result: list[Decimal] = []
    for i in range(period, len(returns) + 1):
        window = returns[i - period : i]
        mean = sum(window) / period
        variance = sum((r - mean) ** 2 for r in window) / period
        vol = variance.sqrt() if variance > 0 else Decimal(0)
        result.append(vol)

    return result


# === Helper Functions ===


def compute_percentage_change(current: Decimal, previous: Decimal) -> Decimal:
    """
    Compute percentage change.

    Args:
        current: Current value.
        previous: Previous value.

    Returns:
        Percentage change (0 if previous is 0).
    """
    if previous == 0:
        return Decimal(0)
    return ((current - previous) / previous) * 100


def compute_log_return(current: Decimal, previous: Decimal) -> Decimal:
    """
    Compute log return.

    Args:
        current: Current price.
        previous: Previous price.

    Returns:
        Log return (0 if previous is 0).
    """
    if previous == 0 or current == 0:
        return Decimal(0)
    return (current / previous).ln()


# === RSI (Relative Strength Index) ===


def compute_rsi(prices: Sequence[Decimal], period: int = 14) -> list[Decimal]:
    """
    Compute Relative Strength Index (batch).

    Args:
        prices: Price series.
        period: RSI period (default 14).

    Returns:
        RSI values (same length as input, first period values are partial).
    """
    if not prices or period <= 0:
        return []

    if len(prices) < 2:
        return [Decimal("50")] * len(prices)

    result: list[Decimal] = []

    # Calculate price changes
    gains: list[Decimal] = []
    losses: list[Decimal] = []

    for i in range(1, len(prices)):
        change = prices[i] - prices[i - 1]
        if change > 0:
            gains.append(change)
            losses.append(Decimal(0))
        else:
            gains.append(Decimal(0))
            losses.append(abs(change))

    # First RSI uses simple average
    if len(gains) < period:
        return [Decimal("50")] * len(prices)

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    # Calculate first RSI
    if avg_loss == 0:
        rsi = Decimal("100")
    else:
        rs = avg_gain / avg_loss
        rsi = Decimal("100") - (Decimal("100") / (Decimal("1") + rs))

    result = [Decimal("50")] * period  # Pad with neutral RSI
    result.append(rsi)

    # Subsequent RSI uses smoothed averages (Wilder's smoothing)
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            rsi = Decimal("100")
        else:
            rs = avg_gain / avg_loss
            rsi = Decimal("100") - (Decimal("100") / (Decimal("1") + rs))

        result.append(rsi)

    return result


