"""
Example: Streaming indicator updates with state management.

Demonstrates using streaming indicator states for efficient real-time updates
in hot-loop scenarios.
"""

from decimal import Decimal

from src.advanced_prep import (
    init_atr_state,
    init_ema_state,
    update_atr_streaming,
    update_ema_streaming,
    RollingWindow,
)


def main() -> None:
    """Run the streaming indicators example."""
    print("=== Streaming Indicator Updates Example ===\n")

    # Initialize streaming states
    ema_fast = init_ema_state(period=12, initial_value=Decimal("50000"))
    ema_slow = init_ema_state(period=26, initial_value=Decimal("50000"))
    atr = init_atr_state(period=14)
    rolling = RollingWindow(20)

    print("Initialized indicators:")
    print(f"  EMA Fast (12)")
    print(f"  EMA Slow (26)")
    print(f"  ATR (14)")
    print(f"  Rolling Window (20)\n")

    # Simulate streaming price updates
    print("Processing streaming price updates...\n")

    base_price = Decimal("50000")

    for i in range(30):
        # Simulate price movement
        price_delta = Decimal(str((i % 20) - 10)) * Decimal("50")
        close = base_price + price_delta
        high = close + Decimal("100")
        low = close - Decimal("100")

        # Update indicators
        ema_fast = update_ema_streaming(ema_fast, close)
        ema_slow = update_ema_streaming(ema_slow, close)
        atr = update_atr_streaming(atr, high, low, close)
        rolling.append(close)

        # Print every 5th update
        if (i + 1) % 5 == 0:
            print(f"Update #{i + 1}:")
            print(f"  Price: {close}")
            print(f"  EMA Fast: {ema_fast.value:.2f}")
            print(f"  EMA Slow: {ema_slow.value:.2f}")

            if atr.tr_window.is_full():
                print(f"  ATR: {atr.value:.2f}")
            else:
                print(f"  ATR: Warming up ({atr.tr_window.count()}/{atr.period})")

            if rolling.is_full():
                print(f"  Rolling Mean: {rolling.mean():.2f}")
                print(f"  Rolling Std: {rolling.std():.2f}")
            else:
                print(f"  Rolling: Warming up ({rolling.count()}/{rolling.size()})")

            print()

    # Final statistics
    print("=== Final Indicator Values ===")
    print(f"EMA Fast (12): {ema_fast.value:.2f}")
    print(f"EMA Slow (26): {ema_slow.value:.2f}")
    print(f"ATR (14): {atr.value:.2f}")
    print(f"Rolling Mean: {rolling.mean():.2f}")
    print(f"Rolling Std: {rolling.std():.2f}")
    print(f"Rolling Min: {rolling.min():.2f}")
    print(f"Rolling Max: {rolling.max():.2f}")

    # Compute crossover signal
    print("\n=== Trading Signal ===")
    if ema_fast.value > ema_slow.value:
        print("EMA Fast > EMA Slow: BULLISH")
    elif ema_fast.value < ema_slow.value:
        print("EMA Fast < EMA Slow: BEARISH")
    else:
        print("EMA Fast = EMA Slow: NEUTRAL")

    # Compute z-score for current position
    from src.advanced_prep import compute_z_score

    current_price = base_price  # Use base as reference
    z_score = compute_z_score(current_price, rolling.mean(), rolling.std())
    print(f"\nCurrent Price Z-Score: {z_score:.2f}")

    if abs(z_score) > 2:
        print("  -> Extreme deviation (>2 std)")
    elif abs(z_score) > 1:
        print("  -> Moderate deviation (>1 std)")
    else:
        print("  -> Normal range")

    print("\n=== Example Complete ===")


if __name__ == "__main__":
    main()

