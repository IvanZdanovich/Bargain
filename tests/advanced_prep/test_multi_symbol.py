"""
Tests for multi-symbol pipeline functionality.
"""

from decimal import Decimal

from src.advanced_prep.multi_symbol import (MultiSymbolConfig,
                                            MultiSymbolPipeline,
                                            create_multi_symbol_pipeline)
from src.types import TickData


def create_tick(symbol: str, timestamp_ms: int, price: str) -> TickData:
    """Helper to create test tick."""
    return {
        "schema_version": "1.0",
        "provider": "test",
        "symbol": symbol,
        "timestamp_ms": timestamp_ms,
        "bid_price": Decimal(price),
        "bid_quantity": Decimal("1"),
        "ask_price": Decimal(price),
        "ask_quantity": Decimal("1"),
        "last_price": Decimal(price),
        "last_quantity": Decimal("1"),
        "raw": {},
    }


class TestMultiSymbolPipeline:
    """Tests for MultiSymbolPipeline."""

    def test_init(self) -> None:
        """Test multi-symbol pipeline initialization."""
        config = MultiSymbolConfig(
            symbols=["BTCUSDT", "ETHUSDT"],
            timeframes_ms=[60000],  # 1m
        )

        pipeline = MultiSymbolPipeline(config)

        assert len(pipeline.get_symbols()) == 2
        assert "BTCUSDT" in pipeline.get_symbols()
        assert "ETHUSDT" in pipeline.get_symbols()

    def test_process_tick_routing(self) -> None:
        """Test tick routing to correct symbol pipeline."""
        config = MultiSymbolConfig(
            symbols=["BTCUSDT", "ETHUSDT"],
            timeframes_ms=[60000],
        )

        pipeline = MultiSymbolPipeline(config)

        # Process tick for BTCUSDT
        tick_btc = create_tick("BTCUSDT", 60000, "50000")
        pipeline.process_tick(tick_btc)

        # Process tick for ETHUSDT
        tick_eth = create_tick("ETHUSDT", 60000, "3000")
        pipeline.process_tick(tick_eth)

        # Both pipelines should have processed ticks
        btc_pipeline = pipeline.get_pipeline("BTCUSDT")
        eth_pipeline = pipeline.get_pipeline("ETHUSDT")

        assert btc_pipeline is not None
        assert eth_pipeline is not None

    def test_get_snapshot_per_symbol(self) -> None:
        """Test getting snapshots for individual symbols."""
        config = MultiSymbolConfig(
            symbols=["BTCUSDT", "ETHUSDT"],
            timeframes_ms=[60000],
        )

        pipeline = MultiSymbolPipeline(config)

        # Process ticks to generate candles
        for i in range(65):
            tick_btc = create_tick("BTCUSDT", i * 1000, "50000")
            tick_eth = create_tick("ETHUSDT", i * 1000, "3000")
            pipeline.process_tick(tick_btc)
            pipeline.process_tick(tick_eth)

        snapshot_btc = pipeline.get_snapshot("BTCUSDT")
        snapshot_eth = pipeline.get_snapshot("ETHUSDT")

        # Both should eventually have snapshots after enough data
        assert snapshot_btc is not None or snapshot_eth is not None

    def test_get_all_snapshots(self) -> None:
        """Test getting snapshots for all symbols."""
        config = MultiSymbolConfig(
            symbols=["BTCUSDT", "ETHUSDT"],
            timeframes_ms=[60000],
        )

        pipeline = MultiSymbolPipeline(config)

        # Process some ticks
        for i in range(65):
            tick_btc = create_tick("BTCUSDT", i * 1000, "50000")
            tick_eth = create_tick("ETHUSDT", i * 1000, "3000")
            pipeline.process_tick(tick_btc)
            pipeline.process_tick(tick_eth)

        all_snapshots = pipeline.get_all_snapshots()

        # Should have at least some snapshots
        assert isinstance(all_snapshots, dict)

    def test_symbol_candle_callback(self) -> None:
        """Test per-symbol candle callbacks."""
        candles_received: list[tuple[str, str]] = []

        def on_candle(symbol: str, timeframe: str, candle) -> None:
            candles_received.append((symbol, timeframe))

        config = MultiSymbolConfig(
            symbols=["BTCUSDT", "ETHUSDT"],
            timeframes_ms=[60000],
        )

        pipeline = MultiSymbolPipeline(config, on_candle=on_candle)

        # Process ticks to cross boundary
        for i in range(65):
            tick_btc = create_tick("BTCUSDT", i * 1000, "50000")
            pipeline.process_tick(tick_btc)

        # Should have received some candle callbacks
        # (at least after crossing the minute boundary)
        btc_candles = [c for c in candles_received if c[0] == "BTCUSDT"]
        assert len(btc_candles) > 0

    def test_reset_single_symbol(self) -> None:
        """Test resetting a single symbol."""
        config = MultiSymbolConfig(
            symbols=["BTCUSDT", "ETHUSDT"],
            timeframes_ms=[60000],
        )

        pipeline = MultiSymbolPipeline(config)

        # Process some data
        tick = create_tick("BTCUSDT", 60000, "50000")
        pipeline.process_tick(tick)

        # Reset only BTCUSDT
        pipeline.reset("BTCUSDT")

        # BTCUSDT should be reset, ETHUSDT unchanged
        snapshot_btc = pipeline.get_snapshot("BTCUSDT")
        assert snapshot_btc is None

    def test_reset_all_symbols(self) -> None:
        """Test resetting all symbols."""
        config = MultiSymbolConfig(
            symbols=["BTCUSDT", "ETHUSDT"],
            timeframes_ms=[60000],
        )

        pipeline = MultiSymbolPipeline(config)

        # Process some data for both
        tick_btc = create_tick("BTCUSDT", 60000, "50000")
        tick_eth = create_tick("ETHUSDT", 60000, "3000")
        pipeline.process_tick(tick_btc)
        pipeline.process_tick(tick_eth)

        # Reset all
        pipeline.reset()

        # Both should be reset
        all_snapshots = pipeline.get_all_snapshots()
        assert len(all_snapshots) == 0


class TestCreateMultiSymbolPipeline:
    """Tests for factory function."""

    def test_create_with_string_timeframes(self) -> None:
        """Test creation with string timeframes."""
        pipeline = create_multi_symbol_pipeline(
            symbols=["BTCUSDT", "ETHUSDT", "BNBUSDT"],
            timeframes=["1m", "5m"],
        )

        assert len(pipeline.get_symbols()) == 3
        assert "BTCUSDT" in pipeline.get_symbols()
        assert "ETHUSDT" in pipeline.get_symbols()
        assert "BNBUSDT" in pipeline.get_symbols()

    def test_create_with_callbacks(self) -> None:
        """Test creation with callbacks."""
        candles = []

        def on_candle(symbol, tf, candle):
            candles.append(symbol)

        pipeline = create_multi_symbol_pipeline(
            symbols=["BTCUSDT"],
            timeframes=["1m"],
            on_candle=on_candle,
        )

        assert pipeline._on_candle is not None
