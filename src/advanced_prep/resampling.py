"""
Tick-to-candle resampling with incremental updates.

Converts tick data into OHLCV candles with VWAP, supporting streaming updates.
"""

from src.types import ResampledCandleData, TickData


class CandleResampler:
    """
    Incremental tick-to-candle resampler.

    Args:
        timeframe_ms: Candle timeframe in milliseconds.

    Side effects:
        Maintains internal state for current candle.
    """

    def __init__(self, timeframe_ms: int) -> None:
        """Initialize resampler with timeframe."""
        if timeframe_ms <= 0:
            raise ValueError(f"Timeframe must be positive, got {timeframe_ms}")
        self._timeframe_ms = timeframe_ms
        self._current_candle: ResampledCandleData | None = None

    def update_tick(self, tick: TickData) -> ResampledCandleData | None:
        """
        Update resampler with new tick.

        Args:
            tick: Normalized tick data.

        Returns:
            Finalized candle if timeframe boundary crossed, else None.

        Side effects:
            Updates internal candle state.
        """
        timestamp_ms = tick["timestamp_ms"]
        price = tick["last_price"]
        quantity = tick["last_quantity"]

        # Determine candle open time (floor to timeframe)
        candle_open_time = (timestamp_ms // self._timeframe_ms) * self._timeframe_ms
        candle_close_time = candle_open_time + self._timeframe_ms

        # Check if we need to finalize current candle
        finalized_candle = None
        if self._current_candle and candle_open_time >= self._current_candle["close_time_ms"]:
            finalized_candle = self._finalize_candle()

        # Initialize or update current candle
        if (
            self._current_candle is None
            or candle_open_time >= self._current_candle["close_time_ms"]
        ):
            self._current_candle = {  # type: ignore[typeddict-item]
                "open_time_ms": candle_open_time,
                "close_time_ms": candle_close_time,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": quantity,
                "vwap": price,
                "tick_count": 1,
                "is_finalized": False,
            }
        else:
            # Update existing candle
            self._current_candle["high"] = max(self._current_candle["high"], price)
            self._current_candle["low"] = min(self._current_candle["low"], price)
            self._current_candle["close"] = price

            # Update VWAP: new_vwap = (old_vwap * old_volume + price * quantity) / new_volume
            old_volume = self._current_candle["volume"]
            old_vwap = self._current_candle["vwap"]
            new_volume = old_volume + quantity

            if new_volume > 0:
                self._current_candle["vwap"] = (
                    old_vwap * old_volume + price * quantity
                ) / new_volume

            self._current_candle["volume"] = new_volume
            self._current_candle["tick_count"] += 1

        return finalized_candle

    def finalize_candle(self, timestamp_ms: int) -> ResampledCandleData | None:
        """
        Force finalization of current candle at boundary.

        Args:
            timestamp_ms: Current timestamp to check boundary.

        Returns:
            Finalized candle if one exists and boundary is reached, else None.

        Side effects:
            Clears current candle state if finalized.
        """
        if self._current_candle is None:
            return None

        candle_open_time = (timestamp_ms // self._timeframe_ms) * self._timeframe_ms
        if candle_open_time >= self._current_candle["close_time_ms"]:
            return self._finalize_candle()

        return None

    def _finalize_candle(self) -> ResampledCandleData:
        """
        Internal: finalize and clear current candle.

        Returns:
            Finalized candle with is_finalized=True.

        Side effects:
            Clears current candle state.
        """
        if self._current_candle is None:
            raise RuntimeError("No candle to finalize")

        finalized = self._current_candle.copy()
        finalized["is_finalized"] = True
        self._current_candle = None
        return finalized

    def get_current_candle(self) -> ResampledCandleData | None:
        """
        Get current (unfilled) candle.

        Returns:
            Current candle or None if no active candle.
        """
        return self._current_candle.copy() if self._current_candle else None

    def reset(self) -> None:
        """
        Reset resampler state.

        Side effects:
            Clears current candle.
        """
        self._current_candle = None


def parse_timeframe_to_ms(timeframe: str) -> int:
    """
    Parse timeframe string to milliseconds.

    Args:
        timeframe: Timeframe string (e.g., "1s", "1m", "5m", "1h", "1d").

    Returns:
        Timeframe in milliseconds.

    Raises:
        ValueError: If timeframe format is invalid.
    """
    timeframe = timeframe.strip().lower()

    if not timeframe:
        raise ValueError("Timeframe cannot be empty")

    # Extract number and unit
    unit = timeframe[-1]
    try:
        value = int(timeframe[:-1])
    except ValueError as e:
        raise ValueError(f"Invalid timeframe format: {timeframe}") from e

    if value <= 0:
        raise ValueError(f"Timeframe value must be positive: {timeframe}")

    # Convert to milliseconds
    multipliers = {
        "s": 1000,
        "m": 60 * 1000,
        "h": 60 * 60 * 1000,
        "d": 24 * 60 * 60 * 1000,
    }

    if unit not in multipliers:
        raise ValueError(f"Invalid timeframe unit '{unit}' in {timeframe}. Use s/m/h/d.")

    return value * multipliers[unit]


def format_timeframe(timeframe_ms: int) -> str:
    """
    Format milliseconds to timeframe string.

    Args:
        timeframe_ms: Timeframe in milliseconds.

    Returns:
        Formatted timeframe string (e.g., "1m", "5m").
    """
    # Convert to largest unit that divides evenly
    if timeframe_ms % (24 * 60 * 60 * 1000) == 0:
        return f"{timeframe_ms // (24 * 60 * 60 * 1000)}d"
    if timeframe_ms % (60 * 60 * 1000) == 0:
        return f"{timeframe_ms // (60 * 60 * 1000)}h"
    if timeframe_ms % (60 * 1000) == 0:
        return f"{timeframe_ms // (60 * 1000)}m"
    return f"{timeframe_ms // 1000}s"
