"""
Example: Multi-timeframe live pipeline with indicators.

Demonstrates setting up a multi-timeframe pipeline that processes ticks
and computes indicators across multiple timeframes in real-time.
"""

from decimal import Decimal

from src.advanced_prep import MultiTimeframePipeline, PipelineConfig
from src.types import MultiTimeframeSnapshotData, ResampledCandleData, TickData


def on_candle_finalized(timeframe: str, candle: ResampledCandleData) -> None:
    """
    Callback when a candle is finalized.

    Args:
        timeframe: Timeframe string (e.g., "1m").
        candle: Finalized candle data.
    """
    print(f"\n[{timeframe}] Candle Finalized:")
    print(f"  Open Time: {candle['open_time_ms']}")
    print(f"  OHLC: O={candle['open']}, H={candle['high']}, L={candle['low']}, C={candle['close']}")
    print(f"  Volume: {candle['volume']}")
    print(f"  VWAP: {candle['vwap']}")
    print(f"  Ticks: {candle['tick_count']}")


def on_multi_tf_ready(snapshot: MultiTimeframeSnapshotData) -> None:
    """
    Callback when all timeframes are updated.

    Args:
        snapshot: Multi-timeframe snapshot with candles and indicators.
    """
    print(f"\n=== Multi-Timeframe Snapshot at {snapshot['timestamp_ms']} ===")
    print(f"Symbol: {snapshot['symbol']}")

    for tf, candle in snapshot["candles"].items():
        print(f"\n[{tf}] Close: {candle['close']}")

        if tf in snapshot["indicators"]:
            indicators = snapshot["indicators"][tf]
            for name, value in indicators.items():
                print(f"  {name}: {value}")


def create_sample_tick(timestamp_ms: int, price: Decimal, quantity: Decimal) -> TickData:
    """
    Create a sample tick for demonstration.

    Args:
        timestamp_ms: Tick timestamp.
        price: Last price.
        quantity: Last quantity.

    Returns:
        TickData.
    """
    return {
        "schema_version": "1.0",
        "provider": "example",
        "symbol": "BTCUSDT",
        "timestamp_ms": timestamp_ms,
        "bid_price": price - Decimal("1"),
        "bid_quantity": Decimal("10"),
        "ask_price": price + Decimal("1"),
        "ask_quantity": Decimal("10"),
        "last_price": price,
        "last_quantity": quantity,
        "raw": {},
    }


def main() -> None:
    """Run the multi-timeframe live pipeline example."""
    print("=== Multi-Timeframe Live Pipeline Example ===\n")

    # Configure pipeline with multiple timeframes
    config = PipelineConfig(
        symbol="BTCUSDT",
        timeframes_ms=[
            60_000,      # 1 minute
            300_000,     # 5 minutes
            3_600_000,   # 1 hour
        ],
        ema_fast_period=12,
        ema_slow_period=26,
        atr_period=14,
        rolling_window_size=20,
        compute_heiken_ashi_enabled=True,
    )

    # Create pipeline with callbacks
    pipeline = MultiTimeframePipeline(
        config=config,
        on_candle=on_candle_finalized,
        on_multi_tf_ready=on_multi_tf_ready,
    )

    print("Pipeline initialized with timeframes: 1m, 5m, 1h")
    print("Indicators: EMA(12), EMA(26), ATR(14), Rolling(20)\n")

    # Simulate incoming ticks
    print("Simulating tick stream...\n")

    base_time = 0
    base_price = Decimal("50000")

    # Generate ticks for ~2 minutes to see candle finalization
    for i in range(130):
        timestamp_ms = base_time + i * 1000  # 1 tick per second

        # Add some price movement
        price_delta = Decimal(str((i % 10) - 5)) * Decimal("10")
        price = base_price + price_delta

        quantity = Decimal("0.5")

        tick = create_sample_tick(timestamp_ms, price, quantity)
        pipeline.process_tick(tick)

    # Get final snapshot
    print("\n\n=== Final Snapshot ===")
    snapshot = pipeline.get_snapshot()

    if snapshot:
        print(f"Symbol: {snapshot['symbol']}")
        print(f"Timestamp: {snapshot['timestamp_ms']}")
        print(f"\nTimeframes with data: {list(snapshot['candles'].keys())}")

        for tf in snapshot["candles"]:
            print(f"\n[{tf}]:")
            candle = snapshot["candles"][tf]
            print(f"  Last Close: {candle['close']}")

            if tf in snapshot["indicators"]:
                print("  Indicators:")
                for name, value in snapshot["indicators"][tf].items():
                    print(f"    {name}: {value}")

    print("\n=== Example Complete ===")


if __name__ == "__main__":
    main()

