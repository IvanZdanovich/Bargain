"""
Example: Multi-symbol pipeline with RSI and candle patterns.

Demonstrates using the multi-symbol pipeline to track multiple trading pairs
simultaneously with RSI indicator and candle pattern detection.
"""

from decimal import Decimal

from src.advanced_prep import (
    create_multi_symbol_pipeline,
    detect_candle_pattern,
)
from src.types import MultiTimeframeSnapshotData, TickData


def create_sample_tick(symbol: str, timestamp_ms: int, price: Decimal) -> TickData:
    """Create a sample tick for demonstration."""
    return {
        "schema_version": "1.0",
        "provider": "example",
        "symbol": symbol,
        "timestamp_ms": timestamp_ms,
        "bid_price": price - Decimal("1"),
        "bid_quantity": Decimal("10"),
        "ask_price": price + Decimal("1"),
        "ask_quantity": Decimal("10"),
        "last_price": price,
        "last_quantity": Decimal("0.5"),
        "raw": {},
    }


def analyze_symbol(symbol: str, snapshot: MultiTimeframeSnapshotData) -> None:
    """Analyze a single symbol's snapshot."""
    print(f"\n=== {symbol} Analysis ===")

    # Get indicators
    indicators_1m = snapshot["indicators"].get("1m", {})
    candles = snapshot["candles"]

    # Display RSI
    if "rsi" in indicators_1m:
        rsi = indicators_1m["rsi"]
        print(f"RSI(14): {rsi:.2f}")

        if rsi < 30:
            print("  → OVERSOLD condition")
        elif rsi > 70:
            print("  → OVERBOUGHT condition")
        else:
            print("  → Normal range")

    # Display EMAs
    if "ema_fast" in indicators_1m and "ema_slow" in indicators_1m:
        ema_fast = indicators_1m["ema_fast"]
        ema_slow = indicators_1m["ema_slow"]
        print(f"EMA Fast: {ema_fast:.2f}")
        print(f"EMA Slow: {ema_slow:.2f}")

        if ema_fast > ema_slow:
            print("  → Bullish trend (EMA crossover)")
        else:
            print("  → Bearish trend")

    # Display ATR
    if "atr" in indicators_1m:
        atr = indicators_1m["atr"]
        print(f"ATR(14): {atr:.2f}")

    # Detect candle patterns (need history)
    if "1m" in candles:
        print("\nCandle Pattern Detection:")
        print("  (Pattern detection requires multiple candles)")


def on_symbol_ready(symbol: str, snapshot: MultiTimeframeSnapshotData) -> None:
    """Callback when a symbol's snapshot is updated."""
    analyze_symbol(symbol, snapshot)


def on_all_symbols_ready(snapshots: dict[str, MultiTimeframeSnapshotData]) -> None:
    """Callback when all symbols have new data."""
    print("\n" + "=" * 60)
    print("ALL SYMBOLS UPDATED - Cross-Symbol Analysis")
    print("=" * 60)

    # Compare RSI across symbols
    rsi_values = {}
    for symbol, snapshot in snapshots.items():
        indicators = snapshot["indicators"].get("1m", {})
        if "rsi" in indicators:
            rsi_values[symbol] = indicators["rsi"]

    if rsi_values:
        print("\nRSI Comparison:")
        for symbol, rsi in sorted(rsi_values.items(), key=lambda x: x[1]):
            status = "OVERSOLD" if rsi < 30 else "OVERBOUGHT" if rsi > 70 else "NORMAL"
            print(f"  {symbol}: {rsi:.2f} [{status}]")

        # Find most oversold
        most_oversold = min(rsi_values.items(), key=lambda x: x[1])
        most_overbought = max(rsi_values.items(), key=lambda x: x[1])

        print(f"\nMost Oversold: {most_oversold[0]} (RSI: {most_oversold[1]:.2f})")
        print(f"Most Overbought: {most_overbought[0]} (RSI: {most_overbought[1]:.2f})")


def main() -> None:
    """Run the multi-symbol example."""
    print("=== Multi-Symbol Pipeline with RSI & Patterns ===\n")

    # Create multi-symbol pipeline
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]

    pipeline = create_multi_symbol_pipeline(
        symbols=symbols,
        timeframes=["1m", "5m"],
        on_symbol_ready=on_symbol_ready,
        on_all_symbols_ready=on_all_symbols_ready,
    )

    print(f"Monitoring symbols: {', '.join(symbols)}")
    print("Timeframes: 1m, 5m")
    print("Indicators: EMA(12), EMA(26), ATR(14), RSI(14)\n")

    # Simulate price movements for different symbols
    base_prices = {
        "BTCUSDT": Decimal("50000"),
        "ETHUSDT": Decimal("3000"),
        "BNBUSDT": Decimal("400"),
    }

    # Create different price patterns for each symbol
    price_patterns = {
        "BTCUSDT": [0, 100, 200, 150, 300, 250, 400, 350, 500, 450, 600, 700, 650, 800, 900],
        "ETHUSDT": [0, -10, -20, -15, -30, -25, -40, -35, -50, -45, -60, -55, -70, -65, -80],
        "BNBUSDT": [0, 5, -3, 8, -2, 10, -1, 12, 3, 15, 5, 18, 8, 20, 10],
    }

    # Process ticks for ~2 minutes
    for i in range(130):
        timestamp_ms = i * 1000

        for symbol in symbols:
            pattern_idx = i % len(price_patterns[symbol])
            price_delta = Decimal(str(price_patterns[symbol][pattern_idx]))
            price = base_prices[symbol] + price_delta

            tick = create_sample_tick(symbol, timestamp_ms, price)
            pipeline.process_tick(tick)

    # Final analysis
    print("\n\n" + "=" * 60)
    print("FINAL ANALYSIS")
    print("=" * 60)

    all_snapshots = pipeline.get_all_snapshots()

    for symbol, snapshot in all_snapshots.items():
        analyze_symbol(symbol, snapshot)

    print("\n=== Example Complete ===")


if __name__ == "__main__":
    main()

