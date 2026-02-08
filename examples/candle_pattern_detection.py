"""
Example: Advanced candle pattern detection.

Demonstrates detecting various candle patterns (Doji, Hammer, Engulfing, etc.)
using historical candle data.
"""

from decimal import Decimal

from src.advanced_prep import (
    detect_candle_pattern,
    is_doji,
    is_engulfing_bearish,
    is_engulfing_bullish,
    is_evening_star,
    is_hammer,
    is_morning_star,
    is_shooting_star,
    is_three_black_crows,
    is_three_white_soldiers,
)
from src.types import ResampledCandleData


def create_candle(
    open_time_ms: int,
    open_price: str,
    high: str,
    low: str,
    close: str,
) -> ResampledCandleData:
    """Create a sample candle."""
    return {
        "open_time_ms": open_time_ms,
        "close_time_ms": open_time_ms + 60000,
        "open": Decimal(open_price),
        "high": Decimal(high),
        "low": Decimal(low),
        "close": Decimal(close),
        "volume": Decimal("100"),
        "vwap": Decimal(close),
        "tick_count": 100,
        "is_finalized": True,
    }


def print_candle_info(candle: ResampledCandleData, label: str = "") -> None:
    """Print candle information."""
    if label:
        print(f"{label}:")
    print(f"  Open: {candle['open']}, High: {candle['high']}, "
          f"Low: {candle['low']}, Close: {candle['close']}")


def main() -> None:
    """Run the candle pattern detection example."""
    print("=== Advanced Candle Pattern Detection ===\n")

    # Example 1: Doji Pattern
    print("1. DOJI PATTERN")
    print("-" * 40)
    doji = create_candle(0, "100", "105", "95", "100.5")
    print_candle_info(doji, "Candle")
    if is_doji(doji):
        print("✓ DOJI detected - Indecision in market")
    print()

    # Example 2: Hammer Pattern
    print("2. HAMMER PATTERN (Bullish Reversal)")
    print("-" * 40)
    hammer = create_candle(60000, "99", "100", "90", "99.5")
    print_candle_info(hammer, "Candle")
    if is_hammer(hammer, trend="down"):
        print("✓ HAMMER detected - Potential bullish reversal after downtrend")
    print()

    # Example 3: Shooting Star Pattern
    print("3. SHOOTING STAR PATTERN (Bearish Reversal)")
    print("-" * 40)
    shooting_star = create_candle(120000, "100", "110", "99", "100.5")
    print_candle_info(shooting_star, "Candle")
    if is_shooting_star(shooting_star):
        print("✓ SHOOTING STAR detected - Potential bearish reversal")
    print()

    # Example 4: Bullish Engulfing
    print("4. BULLISH ENGULFING PATTERN")
    print("-" * 40)
    bearish_candle = create_candle(180000, "105", "105", "100", "100")
    bullish_candle = create_candle(240000, "99", "110", "98", "109")
    print_candle_info(bearish_candle, "Previous (Bearish)")
    print_candle_info(bullish_candle, "Current (Bullish)")
    if is_engulfing_bullish(bullish_candle, bearish_candle):
        print("✓ BULLISH ENGULFING detected - Strong bullish reversal signal")
    print()

    # Example 5: Bearish Engulfing
    print("5. BEARISH ENGULFING PATTERN")
    print("-" * 40)
    small_bullish = create_candle(300000, "100", "105", "100", "105")
    large_bearish = create_candle(360000, "106", "107", "95", "96")
    print_candle_info(small_bullish, "Previous (Bullish)")
    print_candle_info(large_bearish, "Current (Bearish)")
    if is_engulfing_bearish(large_bearish, small_bullish):
        print("✓ BEARISH ENGULFING detected - Strong bearish reversal signal")
    print()

    # Example 6: Morning Star
    print("6. MORNING STAR PATTERN (Bullish Reversal)")
    print("-" * 40)
    candle1 = create_candle(420000, "105", "105", "100", "100")  # Bearish
    candle2 = create_candle(480000, "100", "101", "99", "100")   # Small/Star
    candle3 = create_candle(540000, "100", "110", "100", "108")  # Bullish
    print_candle_info(candle1, "Day 1 (Bearish)")
    print_candle_info(candle2, "Day 2 (Star)")
    print_candle_info(candle3, "Day 3 (Bullish)")
    if is_morning_star(candle1, candle2, candle3):
        print("✓ MORNING STAR detected - Strong bullish reversal after downtrend")
    print()

    # Example 7: Evening Star
    print("7. EVENING STAR PATTERN (Bearish Reversal)")
    print("-" * 40)
    candle1 = create_candle(600000, "100", "105", "100", "105")  # Bullish
    candle2 = create_candle(660000, "105", "106", "104", "105")  # Small/Star
    candle3 = create_candle(720000, "105", "105", "95", "97")    # Bearish
    print_candle_info(candle1, "Day 1 (Bullish)")
    print_candle_info(candle2, "Day 2 (Star)")
    print_candle_info(candle3, "Day 3 (Bearish)")
    if is_evening_star(candle1, candle2, candle3):
        print("✓ EVENING STAR detected - Strong bearish reversal after uptrend")
    print()

    # Example 8: Three White Soldiers
    print("8. THREE WHITE SOLDIERS PATTERN (Strong Bullish)")
    print("-" * 40)
    soldier1 = create_candle(780000, "100", "103", "100", "103")
    soldier2 = create_candle(840000, "102", "106", "102", "106")
    soldier3 = create_candle(900000, "105", "109", "105", "109")
    print_candle_info(soldier1, "Candle 1")
    print_candle_info(soldier2, "Candle 2")
    print_candle_info(soldier3, "Candle 3")
    if is_three_white_soldiers(soldier1, soldier2, soldier3):
        print("✓ THREE WHITE SOLDIERS detected - Very strong bullish continuation")
    print()

    # Example 9: Three Black Crows
    print("9. THREE BLACK CROWS PATTERN (Strong Bearish)")
    print("-" * 40)
    crow1 = create_candle(960000, "109", "109", "106", "106")
    crow2 = create_candle(1020000, "107", "107", "103", "103")
    crow3 = create_candle(1080000, "104", "104", "100", "100")
    print_candle_info(crow1, "Candle 1")
    print_candle_info(crow2, "Candle 2")
    print_candle_info(crow3, "Candle 3")
    if is_three_black_crows(crow1, crow2, crow3):
        print("✓ THREE BLACK CROWS detected - Very strong bearish continuation")
    print()

    # Example 10: Automated Pattern Detection
    print("10. AUTOMATED PATTERN DETECTION")
    print("-" * 40)
    print("Testing multiple candles with detect_candle_pattern():\n")

    test_candles = [
        create_candle(0, "100", "105", "95", "100"),  # Potential Doji
        create_candle(60000, "99", "100", "90", "99"),  # Potential Hammer
        create_candle(120000, "98", "110", "97", "108"),  # Engulfing
    ]

    for i, candle in enumerate(test_candles, 1):
        patterns = detect_candle_pattern(test_candles[:i])
        print(f"Candle {i}:")
        print_candle_info(candle)
        if patterns:
            print(f"  Detected patterns: {', '.join(patterns)}")
        else:
            print("  No patterns detected")
        print()

    # Trading Signals Based on Patterns
    print("\n" + "=" * 60)
    print("TRADING SIGNALS INTERPRETATION")
    print("=" * 60)
    print("""
Bullish Reversal Signals:
  • Hammer - Buy signal after downtrend
  • Bullish Engulfing - Strong buy signal
  • Morning Star - Very strong buy signal
  • Three White Soldiers - Continuation buy

Bearish Reversal Signals:
  • Shooting Star - Sell signal after uptrend
  • Bearish Engulfing - Strong sell signal
  • Evening Star - Very strong sell signal
  • Three Black Crows - Continuation sell

Indecision Signals:
  • Doji - Wait for confirmation
  • Spinning Top - Market uncertainty
    """)

    print("=== Example Complete ===")


if __name__ == "__main__":
    main()

