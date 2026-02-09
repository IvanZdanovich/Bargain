"""
Multi-symbol pipeline manager for concurrent symbol processing.

Manages multiple MultiTimeframePipeline instances for different symbols
with efficient resource sharing and coordinated updates.
"""

from collections.abc import Callable
from dataclasses import dataclass

from src.advanced_prep.pipelines import MultiTimeframePipeline, PipelineConfig
from src.types import (
    CandleEmitFn,
    MultiTimeframeReadyFn,
    MultiTimeframeSnapshotData,
    ResampledCandleData,
    TickData,
)


@dataclass
class MultiSymbolConfig:
    """Configuration for multi-symbol pipeline manager."""

    symbols: list[str]
    timeframes_ms: list[int]
    ema_fast_period: int = 12
    ema_slow_period: int = 26
    atr_period: int = 14
    rsi_period: int = 14
    rolling_window_size: int = 20
    compute_heiken_ashi_enabled: bool = True


SymbolCandleEmitFn = Callable[[str, str, ResampledCandleData], None]
SymbolSnapshotReadyFn = Callable[[str, MultiTimeframeSnapshotData], None]
AllSymbolsReadyFn = Callable[[dict[str, MultiTimeframeSnapshotData]], None]


class MultiSymbolPipeline:
    """
    Multi-symbol pipeline manager.

    Manages separate pipelines for multiple symbols with coordinated updates.

    Args:
        config: Multi-symbol configuration.
        on_candle: Optional callback for each finalized candle (symbol, tf, candle).
        on_symbol_ready: Optional callback when a symbol's snapshot is updated.
        on_all_symbols_ready: Optional callback when all symbols have new data.

    Side effects:
        Maintains pipelines and state for all symbols.
    """

    def __init__(
        self,
        config: MultiSymbolConfig,
        on_candle: SymbolCandleEmitFn | None = None,
        on_symbol_ready: SymbolSnapshotReadyFn | None = None,
        on_all_symbols_ready: AllSymbolsReadyFn | None = None,
    ) -> None:
        """Initialize multi-symbol pipeline manager."""
        self._config = config
        self._on_candle = on_candle
        self._on_symbol_ready = on_symbol_ready
        self._on_all_symbols_ready = on_all_symbols_ready

        # Create pipeline for each symbol
        self._pipelines: dict[str, MultiTimeframePipeline] = {}
        for symbol in config.symbols:
            pipeline_config = PipelineConfig(
                symbol=symbol,
                timeframes_ms=config.timeframes_ms,
                ema_fast_period=config.ema_fast_period,
                ema_slow_period=config.ema_slow_period,
                atr_period=config.atr_period,
                rolling_window_size=config.rolling_window_size,
                compute_heiken_ashi_enabled=config.compute_heiken_ashi_enabled,
            )

            self._pipelines[symbol] = MultiTimeframePipeline(
                config=pipeline_config,
                on_candle=self._wrap_candle_callback(symbol) if on_candle else None,
                on_multi_tf_ready=(
                    self._wrap_snapshot_callback(symbol) if on_symbol_ready else None
                ),
            )

        # Track last update timestamps per symbol
        self._last_updates: dict[str, int] = dict.fromkeys(config.symbols, 0)
        self._snapshots: dict[str, MultiTimeframeSnapshotData | None] = dict.fromkeys(
            config.symbols, None
        )

    def _wrap_candle_callback(self, symbol: str) -> CandleEmitFn:
        """
        Wrap candle callback to include symbol.

        Args:
            symbol: Symbol name.

        Returns:
            Wrapped callback function.
        """

        def callback(timeframe: str, candle: ResampledCandleData) -> None:
            if self._on_candle:
                self._on_candle(symbol, timeframe, candle)

        return callback

    def _wrap_snapshot_callback(self, symbol: str) -> MultiTimeframeReadyFn:
        """
        Wrap snapshot callback to include symbol.

        Args:
            symbol: Symbol name.

        Returns:
            Wrapped callback function.
        """

        def callback(snapshot: MultiTimeframeSnapshotData) -> None:
            self._snapshots[symbol] = snapshot
            self._last_updates[symbol] = snapshot["timestamp_ms"]

            if self._on_symbol_ready:
                self._on_symbol_ready(symbol, snapshot)

            # Check if all symbols have recent data
            if self._on_all_symbols_ready and self._all_symbols_updated():
                all_snapshots = {
                    sym: snap
                    for sym, snap in self._snapshots.items()
                    if snap is not None
                }
                if len(all_snapshots) == len(self._config.symbols):
                    self._on_all_symbols_ready(all_snapshots)

        return callback

    def _all_symbols_updated(self) -> bool:
        """
        Check if all symbols have been updated recently.

        Returns:
            True if all symbols have snapshots.
        """
        return all(snap is not None for snap in self._snapshots.values())

    def process_tick(self, tick: TickData) -> None:
        """
        Process incoming tick for its symbol.

        Args:
            tick: Normalized tick data.

        Side effects:
            Routes tick to appropriate symbol pipeline.
        """
        symbol = tick["symbol"]
        if symbol in self._pipelines:
            self._pipelines[symbol].process_tick(tick)

    def get_pipeline(self, symbol: str) -> MultiTimeframePipeline | None:
        """
        Get pipeline for specific symbol.

        Args:
            symbol: Symbol name.

        Returns:
            Pipeline for symbol or None if not found.
        """
        return self._pipelines.get(symbol)

    def get_snapshot(self, symbol: str) -> MultiTimeframeSnapshotData | None:
        """
        Get current snapshot for symbol.

        Args:
            symbol: Symbol name.

        Returns:
            Snapshot or None if not available.
        """
        pipeline = self._pipelines.get(symbol)
        return pipeline.get_snapshot() if pipeline else None

    def get_all_snapshots(self) -> dict[str, MultiTimeframeSnapshotData]:
        """
        Get snapshots for all symbols.

        Returns:
            Dictionary of symbol -> snapshot (only symbols with data).
        """
        snapshots: dict[str, MultiTimeframeSnapshotData] = {}
        for symbol, pipeline in self._pipelines.items():
            snapshot = pipeline.get_snapshot()
            if snapshot:
                snapshots[symbol] = snapshot
        return snapshots

    def get_symbols(self) -> list[str]:
        """
        Get list of managed symbols.

        Returns:
            List of symbol names.
        """
        return list(self._pipelines.keys())

    def reset(self, symbol: str | None = None) -> None:
        """
        Reset pipeline state.

        Args:
            symbol: Symbol to reset (None = reset all).

        Side effects:
            Clears state for specified symbol(s).
        """
        if symbol:
            if symbol in self._pipelines:
                self._pipelines[symbol].reset()
                self._snapshots[symbol] = None
                self._last_updates[symbol] = 0
        else:
            for pipeline in self._pipelines.values():
                pipeline.reset()
            self._snapshots = dict.fromkeys(self._config.symbols, None)
            self._last_updates = dict.fromkeys(self._config.symbols, 0)


def create_multi_symbol_pipeline(
    symbols: list[str],
    timeframes: list[str],
    on_candle: SymbolCandleEmitFn | None = None,
    on_symbol_ready: SymbolSnapshotReadyFn | None = None,
    on_all_symbols_ready: AllSymbolsReadyFn | None = None,
) -> MultiSymbolPipeline:
    """
    Create multi-symbol pipeline with string timeframes.

    Args:
        symbols: List of symbol names.
        timeframes: List of timeframe strings (e.g., ["1m", "5m"]).
        on_candle: Optional candle callback.
        on_symbol_ready: Optional per-symbol snapshot callback.
        on_all_symbols_ready: Optional all-symbols-ready callback.

    Returns:
        Configured MultiSymbolPipeline.
    """
    from src.advanced_prep.resampling import parse_timeframe_to_ms

    timeframes_ms = [parse_timeframe_to_ms(tf) for tf in timeframes]

    config = MultiSymbolConfig(symbols=symbols, timeframes_ms=timeframes_ms)

    return MultiSymbolPipeline(
        config=config,
        on_candle=on_candle,
        on_symbol_ready=on_symbol_ready,
        on_all_symbols_ready=on_all_symbols_ready,
    )
