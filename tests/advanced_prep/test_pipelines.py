"""
Tests for multi-timeframe pipeline.
"""

from decimal import Decimal

from src.advanced_prep.pipelines import MultiTimeframePipeline, PipelineConfig, create_pipeline
from src.types import MultiTimeframeSnapshotData, ResampledCandleData, TickData


def create_test_tick(timestamp_ms: int, price: str, quantity: str = "1") -> TickData:
    """Helper to create test tick."""
    return {
        "schema_version": "1.0",
        "provider": "test",
        "symbol": "BTCUSDT",
        "timestamp_ms": timestamp_ms,
        "bid_price": Decimal(price),
        "bid_quantity": Decimal("1"),
        "ask_price": Decimal(price),
        "ask_quantity": Decimal("1"),
        "last_price": Decimal(price),
        "last_quantity": Decimal(quantity),
        "raw": {},
    }


class TestMultiTimeframePipeline:
    """Tests for MultiTimeframePipeline."""

    def test_init(self) -> None:
        """Test pipeline initialization."""
        config = PipelineConfig(
            symbol="BTCUSDT",
            timeframes_ms=[60000, 300000],  # 1m, 5m
        )

        pipeline = MultiTimeframePipeline(config)

        assert pipeline._config.symbol == "BTCUSDT"
        assert len(pipeline._resamplers) == 2

    def test_process_single_tick(self) -> None:
        """Test processing single tick."""
        config = PipelineConfig(
            symbol="BTCUSDT",
            timeframes_ms=[60000],
        )

        pipeline = MultiTimeframePipeline(config)
        tick = create_test_tick(60000, "50000")

        pipeline.process_tick(tick)

        # No finalized candles yet
        assert pipeline._state.get_last_candle(60000) is None

    def test_candle_finalization_callback(self) -> None:
        """Test candle finalization callback."""
        finalized_candles: list[tuple[str, ResampledCandleData]] = []

        def on_candle(tf: str, candle: ResampledCandleData) -> None:
            finalized_candles.append((tf, candle))

        config = PipelineConfig(
            symbol="BTCUSDT",
            timeframes_ms=[60000],
        )

        pipeline = MultiTimeframePipeline(config, on_candle=on_candle)

        # First candle period
        pipeline.process_tick(create_test_tick(60000, "50000"))
        pipeline.process_tick(create_test_tick(61000, "50100"))

        # Cross boundary
        pipeline.process_tick(create_test_tick(120000, "50200"))

        assert len(finalized_candles) == 1
        assert finalized_candles[0][0] == "1m"
        assert finalized_candles[0][1]["is_finalized"]

    def test_multi_timeframe_snapshot(self) -> None:
        """Test multi-timeframe snapshot generation."""
        snapshots: list[MultiTimeframeSnapshotData] = []

        def on_snapshot(snapshot: MultiTimeframeSnapshotData) -> None:
            snapshots.append(snapshot)

        config = PipelineConfig(
            symbol="BTCUSDT",
            timeframes_ms=[60000, 300000],  # 1m, 5m
        )

        pipeline = MultiTimeframePipeline(config, on_multi_tf_ready=on_snapshot)

        # Process ticks to cross 1m boundary
        pipeline.process_tick(create_test_tick(60000, "50000"))
        pipeline.process_tick(create_test_tick(120000, "50100"))

        # Should have snapshot
        assert len(snapshots) > 0
        snapshot = snapshots[0]
        assert snapshot["symbol"] == "BTCUSDT"
        assert "1m" in snapshot["candles"] or "5m" in snapshot["candles"]

    def test_get_snapshot(self) -> None:
        """Test getting current snapshot."""
        config = PipelineConfig(
            symbol="BTCUSDT",
            timeframes_ms=[60000],
        )

        pipeline = MultiTimeframePipeline(config)

        # No data yet
        snapshot = pipeline.get_snapshot()
        assert snapshot is None

        # Add data
        pipeline.process_tick(create_test_tick(60000, "50000"))
        pipeline.process_tick(create_test_tick(120000, "50100"))

        snapshot = pipeline.get_snapshot()
        assert snapshot is not None

    def test_indicator_computation(self) -> None:
        """Test indicator computation in pipeline."""
        config = PipelineConfig(
            symbol="BTCUSDT",
            timeframes_ms=[60000],
            ema_fast_period=2,
            ema_slow_period=3,
        )

        pipeline = MultiTimeframePipeline(config)

        # Process multiple candles
        for i in range(5):
            tick_time = 60000 + i * 1000
            price = 50000 + i * 100
            pipeline.process_tick(create_test_tick(tick_time, str(price)))

        # Cross boundary to finalize
        pipeline.process_tick(create_test_tick(120000, "50500"))

        snapshot = pipeline.get_snapshot()

        if snapshot and "1m" in snapshot["indicators"]:
            indicators = snapshot["indicators"]["1m"]
            # Should have some indicators computed
            assert isinstance(indicators, dict)

    def test_reset(self) -> None:
        """Test pipeline reset."""
        config = PipelineConfig(
            symbol="BTCUSDT",
            timeframes_ms=[60000],
        )

        pipeline = MultiTimeframePipeline(config)

        pipeline.process_tick(create_test_tick(60000, "50000"))
        pipeline.reset()

        snapshot = pipeline.get_snapshot()
        assert snapshot is None

    def test_candle_history(self) -> None:
        """Test candle history retrieval."""
        config = PipelineConfig(
            symbol="BTCUSDT",
            timeframes_ms=[60000],
        )

        pipeline = MultiTimeframePipeline(config)

        # Generate multiple candles
        for i in range(5):
            start_time = 60000 * (i + 1)
            pipeline.process_tick(create_test_tick(start_time, str(50000 + i * 100)))
            # Finalize by crossing boundary
            if i < 4:
                next_time = 60000 * (i + 2)
                pipeline.process_tick(create_test_tick(next_time, str(50000 + (i + 1) * 100)))

        history = pipeline.get_candle_history(60000, count=3)
        assert len(history) <= 3


class TestCreatePipeline:
    """Tests for pipeline factory function."""

    def test_create_pipeline(self) -> None:
        """Test pipeline creation with string timeframes."""
        pipeline = create_pipeline("BTCUSDT", ["1m", "5m", "1h"])

        assert pipeline._config.symbol == "BTCUSDT"
        assert len(pipeline._config.timeframes_ms) == 3
        assert 60000 in pipeline._config.timeframes_ms  # 1m
        assert 300000 in pipeline._config.timeframes_ms  # 5m
        assert 3600000 in pipeline._config.timeframes_ms  # 1h

    def test_create_pipeline_with_callbacks(self) -> None:
        """Test pipeline creation with callbacks."""
        candles: list[ResampledCandleData] = []

        def on_candle(tf: str, candle: ResampledCandleData) -> None:
            candles.append(candle)

        pipeline = create_pipeline("BTCUSDT", ["1m"], on_candle=on_candle)

        assert pipeline._on_candle is not None
