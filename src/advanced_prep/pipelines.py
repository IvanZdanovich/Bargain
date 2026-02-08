"""
Multi-timeframe pipeline orchestration.

Coordinates resampling, indicator computation, and transforms across multiple
timeframes with deterministic, aligned outputs.
"""

from dataclasses import dataclass
from decimal import Decimal

from src.advanced_prep.indicators import update_atr_streaming, update_ema_streaming
from src.advanced_prep.resampling import CandleResampler, format_timeframe
from src.advanced_prep.state import (
    create_streaming_state,
    get_indicator_values,
    init_indicator_states,
)
from src.advanced_prep.transforms import compute_heiken_ashi
from src.types import (
    CandleEmitFn,
    MultiTimeframeReadyFn,
    MultiTimeframeSnapshotData,
    ResampledCandleData,
    TickData,
)


@dataclass
class PipelineConfig:
    """Configuration for multi-timeframe pipeline."""

    symbol: str
    timeframes_ms: list[int]
    ema_fast_period: int = 12
    ema_slow_period: int = 26
    atr_period: int = 14
    rolling_window_size: int = 20
    compute_heiken_ashi_enabled: bool = True


class MultiTimeframePipeline:
    """
    Multi-timeframe streaming pipeline.

    Processes ticks through multiple resamplers, computes indicators per timeframe,
    and emits aligned snapshots.

    Args:
        config: Pipeline configuration.
        on_candle: Optional callback for each finalized candle.
        on_multi_tf_ready: Optional callback when all timeframes updated.

    Side effects:
        Maintains internal state, emits callbacks.
    """

    def __init__(
        self,
        config: PipelineConfig,
        on_candle: CandleEmitFn | None = None,
        on_multi_tf_ready: MultiTimeframeReadyFn | None = None,
    ) -> None:
        """Initialize pipeline with config and callbacks."""
        self._config = config
        self._on_candle = on_candle
        self._on_multi_tf_ready = on_multi_tf_ready

        # Create resamplers for each timeframe
        self._resamplers: dict[int, CandleResampler] = {
            tf_ms: CandleResampler(tf_ms) for tf_ms in config.timeframes_ms
        }

        # Create streaming state
        self._state = create_streaming_state(config.symbol, config.timeframes_ms)

        # Track which timeframes updated in current tick
        self._updated_timeframes: set[int] = set()

    def process_tick(self, tick: TickData) -> None:
        """
        Process incoming tick through all timeframes.

        Args:
            tick: Normalized tick data.

        Side effects:
            Updates state, emits candle and snapshot callbacks.
        """
        self._state.last_tick_timestamp_ms = tick["timestamp_ms"]
        self._updated_timeframes.clear()

        # Process tick through each resampler
        for tf_ms, resampler in self._resamplers.items():
            finalized_candle = resampler.update_tick(tick)

            if finalized_candle:
                self._handle_finalized_candle(tf_ms, finalized_candle)
                self._updated_timeframes.add(tf_ms)

        # Emit multi-timeframe snapshot if all updated
        if self._updated_timeframes and self._on_multi_tf_ready:
            snapshot = self._build_snapshot()
            if snapshot:
                self._on_multi_tf_ready(snapshot)

    def _handle_finalized_candle(self, tf_ms: int, candle: ResampledCandleData) -> None:
        """
        Handle finalized candle: update state, compute indicators, emit callback.

        Args:
            tf_ms: Timeframe in milliseconds.
            candle: Finalized candle.

        Side effects:
            Updates state, computes indicators, emits callback.
        """
        # Update state
        self._state.update_candle(tf_ms, candle)
        tf_state = self._state.get_or_create_timeframe_state(tf_ms)

        # Initialize indicators if first candle
        if tf_state.indicators.ema_fast is None:
            init_indicator_states(
                tf_state,
                self._config.ema_fast_period,
                self._config.ema_slow_period,
                self._config.atr_period,
                self._config.rolling_window_size,
            )

        # Update indicators
        self._update_indicators(tf_state, candle)

        # Compute Heiken Ashi if enabled
        if self._config.compute_heiken_ashi_enabled:
            ha_candle = compute_heiken_ashi(candle, tf_state.last_ha_candle)
            tf_state.last_ha_candle = ha_candle

        # Emit candle callback
        if self._on_candle:
            tf_str = format_timeframe(tf_ms)
            self._on_candle(tf_str, candle)

    def _update_indicators(self, tf_state, candle: ResampledCandleData) -> None:
        """
        Update all indicators for a timeframe.

        Args:
            tf_state: TimeframeState to update.
            candle: New candle.

        Side effects:
            Updates indicator states.
        """
        close = candle["close"]
        high = candle["high"]
        low = candle["low"]

        # Update EMAs
        if tf_state.indicators.ema_fast:
            tf_state.indicators.ema_fast = update_ema_streaming(
                tf_state.indicators.ema_fast, close
            )

        if tf_state.indicators.ema_slow:
            tf_state.indicators.ema_slow = update_ema_streaming(
                tf_state.indicators.ema_slow, close
            )

        # Update ATR
        if tf_state.indicators.atr:
            tf_state.indicators.atr = update_atr_streaming(
                tf_state.indicators.atr, high, low, close
            )

        # Update rolling window
        if tf_state.indicators.rolling_window:
            tf_state.indicators.rolling_window.append(close)

    def _build_snapshot(self) -> MultiTimeframeSnapshotData | None:
        """
        Build multi-timeframe snapshot from current state.

        Returns:
            Snapshot with all timeframes and indicators, or None if no data.
        """
        candles: dict[str, ResampledCandleData] = {}
        indicators: dict[str, dict[str, Decimal]] = {}

        for tf_ms in self._config.timeframes_ms:
            tf_str = format_timeframe(tf_ms)
            last_candle = self._state.get_last_candle(tf_ms)

            if last_candle:
                candles[tf_str] = last_candle
                tf_state = self._state.get_or_create_timeframe_state(tf_ms)
                indicators[tf_str] = get_indicator_values(tf_state)

        if not candles:
            return None

        return {  # type: ignore[return-value]
            "timestamp_ms": self._state.last_tick_timestamp_ms,
            "symbol": self._config.symbol,
            "candles": candles,
            "indicators": indicators,
            "transforms": {},
        }

    def get_snapshot(self) -> MultiTimeframeSnapshotData | None:
        """
        Get current multi-timeframe snapshot.

        Returns:
            Snapshot or None if no data yet.
        """
        return self._build_snapshot()

    def get_candle_history(self, timeframe_ms: int, count: int = 100) -> list[ResampledCandleData]:
        """
        Get candle history for a timeframe.

        Args:
            timeframe_ms: Timeframe in milliseconds.
            count: Number of candles to retrieve.

        Returns:
            List of historical candles.
        """
        return self._state.get_candle_history(timeframe_ms, count)

    def reset(self) -> None:
        """
        Reset pipeline state.

        Side effects:
            Clears all state and resamplers.
        """
        for resampler in self._resamplers.values():
            resampler.reset()
        self._state.reset()
        self._updated_timeframes.clear()


def create_pipeline(
    symbol: str,
    timeframes: list[str],
    on_candle: CandleEmitFn | None = None,
    on_multi_tf_ready: MultiTimeframeReadyFn | None = None,
) -> MultiTimeframePipeline:
    """
    Create multi-timeframe pipeline with string timeframes.

    Args:
        symbol: Trading symbol.
        timeframes: List of timeframe strings (e.g., ["1m", "5m", "1h"]).
        on_candle: Optional candle callback.
        on_multi_tf_ready: Optional snapshot callback.

    Returns:
        Configured MultiTimeframePipeline.
    """
    from src.advanced_prep.resampling import parse_timeframe_to_ms

    timeframes_ms = [parse_timeframe_to_ms(tf) for tf in timeframes]

    config = PipelineConfig(symbol=symbol, timeframes_ms=timeframes_ms)

    return MultiTimeframePipeline(
        config=config,
        on_candle=on_candle,
        on_multi_tf_ready=on_multi_tf_ready,
    )

