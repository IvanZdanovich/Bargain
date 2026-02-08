"""
Example: Historical batch processing with indicators.

Demonstrates batch computation of indicators on historical price data
and comparison with streaming mode for validation.
"""

from decimal import Decimal

from src.advanced_prep import (
    compute_atr_batch,
    compute_ema,
    compute_sma,
    compute_wma,
)


def main() -> None:
    """Run the historical batch processing example."""
    print("=== Historical Batch Processing Example ===\n")

    # Sample historical closing prices
    close_prices = [
        Decimal("50000"),
        Decimal("50100"),
        Decimal("50200"),
        Decimal("50150"),
        Decimal("50300"),
        Decimal("50250"),
        Decimal("50400"),
        Decimal("50350"),
        Decimal("50500"),
        Decimal("50450"),
        Decimal("50600"),
        Decimal("50700"),
        Decimal("50650"),
        Decimal("50800"),
        Decimal("50900"),
    ]

    # Sample OHLC data for ATR
    highs = [
        Decimal("50100"),
        Decimal("50200"),
        Decimal("50300"),
        Decimal("50250"),
        Decimal("50400"),
        Decimal("50350"),
        Decimal("50500"),
        Decimal("50450"),
        Decimal("50600"),
        Decimal("50550"),
        Decimal("50700"),
        Decimal("50800"),
        Decimal("50750"),
        Decimal("50900"),
        Decimal("51000"),
    ]

    lows = [
        Decimal("49900"),
        Decimal("50000"),
        Decimal("50100"),
        Decimal("50050"),
        Decimal("50200"),
        Decimal("50150"),
        Decimal("50300"),
        Decimal("50250"),
        Decimal("50400"),
        Decimal("50350"),
        Decimal("50500"),
        Decimal("50600"),
        Decimal("50550"),
        Decimal("50700"),
        Decimal("50800"),
    ]

    print(f"Processing {len(close_prices)} historical candles\n")

    # Compute SMA
    sma_period = 5
    sma_values = compute_sma(close_prices, sma_period)
    print(f"SMA({sma_period}):")
    for i, sma in enumerate(sma_values[-5:]):  # Show last 5
        idx = len(close_prices) - len(sma_values) + i
        print(f"  [{idx}] Price: {close_prices[idx]}, SMA: {sma}")

    # Compute EMA
    ema_period = 5
    ema_values = compute_ema(close_prices, ema_period)
    print(f"\nEMA({ema_period}):")
    for i, ema in enumerate(ema_values[-5:]):  # Show last 5
        idx = len(close_prices) - 5 + i
        print(f"  [{idx}] Price: {close_prices[idx]}, EMA: {ema}")

    # Compute WMA
    wma_period = 5
    wma_values = compute_wma(close_prices, wma_period)
    print(f"\nWMA({wma_period}):")
    for i, wma in enumerate(wma_values[-5:]):  # Show last 5
        idx = len(close_prices) - len(wma_values) + i
        print(f"  [{idx}] Price: {close_prices[idx]}, WMA: {wma}")

    # Compute ATR
    atr_period = 5
    atr_values = compute_atr_batch(highs, lows, close_prices, atr_period)
    print(f"\nATR({atr_period}):")
    for i, atr in enumerate(atr_values[-5:]):  # Show last 5
        idx = len(close_prices) - len(atr_values) + i
        print(f"  [{idx}] High: {highs[idx]}, Low: {lows[idx]}, ATR: {atr}")

    # Compare moving averages
    print("\n=== Moving Average Comparison (Last Value) ===")
    if sma_values and ema_values and wma_values:
        print(f"SMA({sma_period}): {sma_values[-1]}")
        print(f"EMA({ema_period}): {ema_values[-1]}")
        print(f"WMA({wma_period}): {wma_values[-1]}")
        print(f"Current Price: {close_prices[-1]}")

    # Compute statistics
    print("\n=== Price Statistics ===")
    price_range = max(close_prices) - min(close_prices)
    avg_price = sum(close_prices) / len(close_prices)
    print(f"Min Price: {min(close_prices)}")
    print(f"Max Price: {max(close_prices)}")
    print(f"Range: {price_range}")
    print(f"Average: {avg_price}")

    print("\n=== Example Complete ===")


if __name__ == "__main__":
    main()

