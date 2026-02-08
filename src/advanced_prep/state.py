"""
State management for streaming mode operations.

Maintains indicator states, rolling windows, and multi-timeframe candle history
for efficient streaming updates.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from src.advanced_prep.indicators import ATRState, EMAState, RSIState
from src.advanced_prep.rolling import RollingWindow
from src.types import HeikenAshiData, ResampledCandleData


@dataclass
class IndicatorStates:
    """Container for all indicator states for a single timeframe."""

    ema_fast: EMAState | None = None
    ema_slow: EMAState | None = None
    ema_signal: EMAState | None = None
    atr: ATRState | None = None
    rsi: RSIState | None = None
    rolling_window: RollingWindow | None = None


@dataclass
class TimeframeState:
    """State for a single timeframe including candles and indicators."""

    timeframe_ms: int
    last_candle: ResampledCandleData | None = None
    prev_candle: ResampledCandleData | None = None
    last_ha_candle: HeikenAshiData | None = None
    indicators: IndicatorStates = field(default_factory=IndicatorStates)
    candle_history: list[ResampledCandleData] = field(default_factory=list)
    max_history: int = 100


@dataclass
class StreamingState:
    """
    Global streaming state for multi-timeframe pipeline.

    Args:
        symbol: Trading symbol.
        timeframes_ms: List of timeframes in milliseconds.

    Side effects:
        Maintains state across tick updates.
    """

    symbol: str
    timeframe_states: dict[int, TimeframeState] = field(default_factory=dict)
    last_tick_timestamp_ms: int = 0

    def get_or_create_timeframe_state(self, timeframe_ms: int) -> TimeframeState:
        """
        Get or create state for a timeframe.

        Args:
            timeframe_ms: Timeframe in milliseconds.

        Returns:
            TimeframeState for the specified timeframe.

        Side effects:
            Creates state if it doesn't exist.
        """
        if timeframe_ms not in self.timeframe_states:
            self.timeframe_states[timeframe_ms] = TimeframeState(timeframe_ms=timeframe_ms)
        return self.timeframe_states[timeframe_ms]

    def update_candle(self, timeframe_ms: int, candle: ResampledCandleData) -> None:
        """
        Update candle for a timeframe.

        Args:
            timeframe_ms: Timeframe in milliseconds.
            candle: New candle.

        Side effects:
            Updates last_candle and candle history.
        """
        state = self.get_or_create_timeframe_state(timeframe_ms)

        # Move last candle to prev if new candle starts different period
        if state.last_candle and candle["open_time_ms"] != state.last_candle["open_time_ms"]:
            state.prev_candle = state.last_candle

            # Add to history if finalized
            if state.last_candle["is_finalized"]:
                state.candle_history.append(state.last_candle)

                # Keep history within limit
                if len(state.candle_history) > state.max_history:
                    state.candle_history = state.candle_history[-state.max_history :]

        state.last_candle = candle

    def get_last_candle(self, timeframe_ms: int) -> ResampledCandleData | None:
        """
        Get last candle for timeframe.

        Args:
            timeframe_ms: Timeframe in milliseconds.

        Returns:
            Last candle or None if no candles yet.
        """
        state = self.timeframe_states.get(timeframe_ms)
        return state.last_candle if state else None

    def get_candle_history(
        self, timeframe_ms: int, count: int | None = None
    ) -> list[ResampledCandleData]:
        """
        Get candle history for timeframe.

        Args:
            timeframe_ms: Timeframe in milliseconds.
            count: Number of candles to retrieve (None = all).

        Returns:
            List of historical candles (oldest first).
        """
        state = self.timeframe_states.get(timeframe_ms)
        if not state:
            return []

        history = state.candle_history
        if count is not None and count > 0:
            history = history[-count:]

        return history

    def reset(self) -> None:
        """
        Reset all state.

        Side effects:
            Clears all timeframe states.
        """
        self.timeframe_states.clear()
        self.last_tick_timestamp_ms = 0


def create_streaming_state(symbol: str, timeframes_ms: list[int]) -> StreamingState:
    """
    Create initial streaming state for symbol and timeframes.

    Args:
        symbol: Trading symbol.
        timeframes_ms: List of timeframes in milliseconds.

    Returns:
        Initialized StreamingState.
    """
    state = StreamingState(symbol=symbol)

    # Pre-create timeframe states
    for tf_ms in timeframes_ms:
        state.get_or_create_timeframe_state(tf_ms)

    return state


def init_indicator_states(
    state: TimeframeState, ema_fast: int, ema_slow: int, atr_period: int, rolling_window: int
) -> None:
    """
    Initialize indicator states for a timeframe.

    Args:
        state: TimeframeState to initialize.
        ema_fast: Fast EMA period.
        ema_slow: Slow EMA period.
        atr_period: ATR period.
        rolling_window: Rolling window size.

    Side effects:
        Creates indicator states in the TimeframeState.
    """
    from src.advanced_prep.indicators import init_atr_state, init_ema_state

    if state.last_candle:
        close_price = state.last_candle["close"]
        state.indicators.ema_fast = init_ema_state(ema_fast, close_price)
        state.indicators.ema_slow = init_ema_state(ema_slow, close_price)

    state.indicators.atr = init_atr_state(atr_period)
    state.indicators.rolling_window = RollingWindow(rolling_window)


def get_indicator_values(state: TimeframeState) -> dict[str, Decimal]:
    """
    Extract current indicator values from state.

    Args:
        state: TimeframeState with indicators.

    Returns:
        Dictionary of indicator name -> value.
    """
    indicators: dict[str, Decimal] = {}

    if state.indicators.ema_fast and state.indicators.ema_fast.initialized:
        indicators["ema_fast"] = state.indicators.ema_fast.value

    if state.indicators.ema_slow and state.indicators.ema_slow.initialized:
        indicators["ema_slow"] = state.indicators.ema_slow.value

    if state.indicators.atr and state.indicators.atr.tr_window.is_full():
        indicators["atr"] = state.indicators.atr.value

    if state.indicators.rsi and state.indicators.rsi.gains.is_full():
        indicators["rsi"] = state.indicators.rsi.value

    if state.indicators.rolling_window and state.indicators.rolling_window.is_full():
        indicators["rolling_mean"] = state.indicators.rolling_window.mean()
        indicators["rolling_std"] = state.indicators.rolling_window.std()

    return indicators

