"""
Tests for RSI indicator and candle pattern detection.
"""

from decimal import Decimal

from src.advanced_prep.indicators import compute_rsi, init_rsi_state, update_rsi_streaming
from src.advanced_prep.transforms import (
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


def create_candle(open_p: str, high: str, low: str, close: str) -> ResampledCandleData:
    """Helper to create test candle."""
    return {
        "open_time_ms": 60000,
        "close_time_ms": 120000,
        "open": Decimal(open_p),
        "high": Decimal(high),
        "low": Decimal(low),
        "close": Decimal(close),
        "volume": Decimal("100"),
        "vwap": Decimal("100"),
        "tick_count": 10,
        "is_finalized": True,
    }


class TestRSI:
    """Tests for RSI indicator."""

    def test_compute_rsi_basic(self) -> None:
        """Test RSI computation with basic data."""
        # Uptrend prices
        prices = [Decimal(str(x)) for x in range(100, 115)]
        result = compute_rsi(prices, period=14)

        assert len(result) == len(prices)
        # RSI should be high in uptrend
        assert result[-1] > Decimal("50")

    def test_compute_rsi_downtrend(self) -> None:
        """Test RSI in downtrend."""
        # Downtrend prices
        prices = [Decimal(str(x)) for x in range(115, 100, -1)]
        result = compute_rsi(prices, period=14)

        # RSI should be low in downtrend
        assert result[-1] < Decimal("50")

    def test_rsi_streaming(self) -> None:
        """Test streaming RSI updates."""
        prices = [Decimal(str(x)) for x in range(100, 120)]

        state = init_rsi_state(14, prices[0])

        for price in prices[1:]:
            state = update_rsi_streaming(state, price)

        # Should have computed RSI after enough data
        assert state.gains.is_full()
        assert Decimal("0") <= state.value <= Decimal("100")

    def test_rsi_edge_cases(self) -> None:
        """Test RSI edge cases."""
        # Empty list
        assert compute_rsi([], 14) == []

        # Single value
        result = compute_rsi([Decimal("100")], 14)
        assert len(result) == 1


class TestCandlePatterns:
    """Tests for candle pattern detection."""

    def test_doji(self) -> None:
        """Test Doji pattern detection."""
        # Perfect doji (open = close)
        candle = create_candle("100", "105", "95", "100")
        assert is_doji(candle)

        # Not a doji (large body)
        candle2 = create_candle("100", "110", "95", "108")
        assert not is_doji(candle2)

    def test_hammer(self) -> None:
        """Test Hammer pattern detection."""
        # Hammer: small body at top, long lower wick
        candle = create_candle("99", "100", "90", "100")
        assert is_hammer(candle, trend="down")

        # Not a hammer (no long wick)
        candle2 = create_candle("95", "100", "94", "100")
        assert not is_hammer(candle2, trend="down")

    def test_shooting_star(self) -> None:
        """Test Shooting Star pattern detection."""
        # Shooting star: small body at bottom, long upper wick
        candle = create_candle("100", "110", "99", "99")
        assert is_shooting_star(candle)

        # Not a shooting star
        candle2 = create_candle("100", "102", "99", "101")
        assert not is_shooting_star(candle2)

    def test_bullish_engulfing(self) -> None:
        """Test Bullish Engulfing pattern."""
        # Small bearish followed by large bullish
        prev_candle = create_candle("105", "105", "100", "100")
        curr_candle = create_candle("99", "110", "98", "110")

        assert is_engulfing_bullish(curr_candle, prev_candle)

    def test_bearish_engulfing(self) -> None:
        """Test Bearish Engulfing pattern."""
        # Small bullish followed by large bearish
        prev_candle = create_candle("100", "105", "100", "105")
        curr_candle = create_candle("106", "106", "95", "95")

        assert is_engulfing_bearish(curr_candle, prev_candle)

    def test_morning_star(self) -> None:
        """Test Morning Star pattern."""
        candle1 = create_candle("105", "105", "100", "100")  # Bearish
        candle2 = create_candle("100", "101", "99", "100")  # Small/doji
        candle3 = create_candle("100", "110", "100", "108")  # Bullish

        assert is_morning_star(candle1, candle2, candle3)

    def test_evening_star(self) -> None:
        """Test Evening Star pattern."""
        candle1 = create_candle("100", "105", "100", "105")  # Bullish
        candle2 = create_candle("105", "106", "104", "105")  # Small/doji
        candle3 = create_candle("105", "105", "95", "97")  # Bearish

        assert is_evening_star(candle1, candle2, candle3)

    def test_three_white_soldiers(self) -> None:
        """Test Three White Soldiers pattern."""
        candle1 = create_candle("100", "103", "100", "103")
        candle2 = create_candle("102", "106", "102", "106")
        candle3 = create_candle("105", "109", "105", "109")

        assert is_three_white_soldiers(candle1, candle2, candle3)

    def test_three_black_crows(self) -> None:
        """Test Three Black Crows pattern."""
        candle1 = create_candle("109", "109", "106", "106")
        candle2 = create_candle("107", "107", "103", "103")
        candle3 = create_candle("104", "104", "100", "100")

        assert is_three_black_crows(candle1, candle2, candle3)

    def test_detect_candle_pattern(self) -> None:
        """Test pattern detection function."""
        # Doji candle
        candles = [create_candle("100", "105", "95", "100")]
        patterns = detect_candle_pattern(candles)
        assert "doji" in patterns

        # Bullish engulfing (need 2 candles)
        candles = [
            create_candle("105", "105", "100", "100"),
            create_candle("99", "110", "98", "110"),
        ]
        patterns = detect_candle_pattern(candles)
        assert "bullish_engulfing" in patterns
