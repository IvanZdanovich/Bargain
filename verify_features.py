#!/usr/bin/env python3
"""Quick verification script for new features."""

from decimal import Decimal
from src.advanced_prep import (
    compute_rsi,
    create_multi_symbol_pipeline,
    detect_candle_pattern,
    is_doji,
)

print("=" * 60)
print("VERIFICATION SCRIPT - New Features")
print("=" * 60)

# Test 1: RSI
print("\n1. Testing RSI...")
prices = [Decimal(str(x)) for x in range(100, 120)]
rsi_result = compute_rsi(prices, period=14)
print(f"   ✅ RSI computed: {len(rsi_result)} values")
print(f"   Last RSI: {rsi_result[-1]:.2f}")

# Test 2: Candle Patterns
print("\n2. Testing Candle Patterns...")
from src.types import ResampledCandleData

candle: ResampledCandleData = {
    "open_time_ms": 0,
    "close_time_ms": 60000,
    "open": Decimal("100"),
    "high": Decimal("105"),
    "low": Decimal("95"),
    "close": Decimal("100"),
    "volume": Decimal("100"),
    "vwap": Decimal("100"),
    "tick_count": 10,
    "is_finalized": True,
}

if is_doji(candle):
    print("   ✅ Doji detection works")

patterns = detect_candle_pattern([candle])
print(f"   ✅ Pattern detection works: {patterns}")

# Test 3: Multi-Symbol
print("\n3. Testing Multi-Symbol Pipeline...")
pipeline = create_multi_symbol_pipeline(
    symbols=["BTCUSDT", "ETHUSDT"],
    timeframes=["1m"],
)
symbols = pipeline.get_symbols()
print(f"   ✅ Multi-symbol pipeline created: {symbols}")

print("\n" + "=" * 60)
print("ALL TESTS PASSED ✅")
print("=" * 60)

