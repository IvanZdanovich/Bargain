"""
Tests for transform functions.
"""

from decimal import Decimal

import pytest

from src.advanced_prep.transforms import (
    compute_candle_body_size,
    compute_candle_range,
    compute_candle_wick_sizes,
    compute_heiken_ashi,
    compute_log_returns_series,
    compute_percentage_returns_series,
    compute_pivot_point,
    compute_support_resistance,
    compute_typical_price,
    is_bearish_candle,
    is_bullish_candle,
    normalize_min_max,
    normalize_z_score,
)
from src.types import ResampledCandleData


def create_test_candle(open_price: str, high: str, low: str, close: str) -> ResampledCandleData:
    """Helper to create test candle."""
    return {
        "open_time_ms": 60000,
        "close_time_ms": 120000,
        "open": Decimal(open_price),
        "high": Decimal(high),
        "low": Decimal(low),
        "close": Decimal(close),
        "volume": Decimal("100"),
        "vwap": Decimal("100"),
        "tick_count": 10,
        "is_finalized": True,
    }


class TestHeikenAshi:
    """Tests for Heiken Ashi transform."""

    def test_first_candle(self) -> None:
        """Test HA computation for first candle."""
        candle = create_test_candle("100", "110", "95", "105")
        ha = compute_heiken_ashi(candle, None)

        # HA Close = (100 + 110 + 95 + 105) / 4 = 102.5
        assert ha["ha_close"] == Decimal("102.5")

        # HA Open (first) = (100 + 105) / 2 = 102.5
        assert ha["ha_open"] == Decimal("102.5")

        # HA High = max(110, 102.5, 102.5) = 110
        assert ha["ha_high"] == Decimal("110")

        # HA Low = min(95, 102.5, 102.5) = 95
        assert ha["ha_low"] == Decimal("95")

    def test_subsequent_candle(self) -> None:
        """Test HA computation with previous HA candle."""
        candle1 = create_test_candle("100", "110", "95", "105")
        ha1 = compute_heiken_ashi(candle1, None)

        candle2 = create_test_candle("105", "115", "100", "110")
        ha2 = compute_heiken_ashi(candle2, ha1)

        # HA Close = (105 + 115 + 100 + 110) / 4 = 107.5
        assert ha2["ha_close"] == Decimal("107.5")

        # HA Open = (prev_ha_open + prev_ha_close) / 2 = (102.5 + 102.5) / 2 = 102.5
        assert ha2["ha_open"] == Decimal("102.5")


class TestReturns:
    """Tests for return computations."""

    def test_compute_log_returns_series(self) -> None:
        """Test log returns series."""
        prices = [Decimal(str(x)) for x in [100, 110, 105]]
        returns = compute_log_returns_series(prices)

        assert len(returns) == 2
        # ln(110/100) = ln(1.1) ≈ 0.0953
        assert abs(returns[0] - Decimal("0.0953")) < Decimal("0.001")

    def test_compute_log_returns_edge_cases(self) -> None:
        """Test log returns edge cases."""
        # Not enough prices
        assert compute_log_returns_series([Decimal("100")]) == []

        # Zero price
        prices = [Decimal("100"), Decimal("0")]
        returns = compute_log_returns_series(prices)
        assert returns[0] == Decimal("0")

    def test_compute_percentage_returns_series(self) -> None:
        """Test percentage returns series."""
        prices = [Decimal(str(x)) for x in [100, 110, 105]]
        returns = compute_percentage_returns_series(prices)

        assert len(returns) == 2
        assert returns[0] == Decimal("10")  # (110-100)/100 * 100
        # (105-110)/110 * 100 = -4.545...
        assert abs(returns[1] - Decimal("-4.545")) < Decimal("0.01")


class TestNormalization:
    """Tests for normalization functions."""

    def test_normalize_min_max(self) -> None:
        """Test min-max normalization."""
        result = normalize_min_max(Decimal("50"), Decimal("0"), Decimal("100"))
        assert result == Decimal("0.5")

        result = normalize_min_max(Decimal("0"), Decimal("0"), Decimal("100"))
        assert result == Decimal("0")

        result = normalize_min_max(Decimal("100"), Decimal("0"), Decimal("100"))
        assert result == Decimal("1")

        # Same min and max
        result = normalize_min_max(Decimal("50"), Decimal("50"), Decimal("50"))
        assert result == Decimal("0")

    def test_normalize_z_score(self) -> None:
        """Test z-score normalization."""
        result = normalize_z_score(Decimal("30"), Decimal("20"), Decimal("5"))
        assert result == Decimal("2")

        result = normalize_z_score(Decimal("10"), Decimal("20"), Decimal("5"))
        assert result == Decimal("-2")

        # Zero std
        result = normalize_z_score(Decimal("30"), Decimal("20"), Decimal("0"))
        assert result == Decimal("0")


class TestPriceHelpers:
    """Tests for price helper functions."""

    def test_compute_typical_price(self) -> None:
        """Test typical price computation."""
        result = compute_typical_price(Decimal("110"), Decimal("90"), Decimal("100"))
        assert result == Decimal("100")  # (110+90+100)/3

    def test_compute_pivot_point(self) -> None:
        """Test pivot point computation."""
        result = compute_pivot_point(Decimal("110"), Decimal("90"), Decimal("100"))
        assert result == Decimal("100")

    def test_compute_support_resistance(self) -> None:
        """Test support/resistance levels."""
        pivot = Decimal("100")
        high = Decimal("110")
        low = Decimal("90")

        r1, r2, s1, s2 = compute_support_resistance(pivot, high, low)

        # R1 = 2*100 - 90 = 110
        assert r1 == Decimal("110")
        # S1 = 2*100 - 110 = 90
        assert s1 == Decimal("90")
        # R2 = 100 + (110 - 90) = 120
        assert r2 == Decimal("120")
        # S2 = 100 - (110 - 90) = 80
        assert s2 == Decimal("80")


class TestCandleAnalysis:
    """Tests for candle analysis functions."""

    def test_is_bullish_candle(self) -> None:
        """Test bullish candle detection."""
        candle = create_test_candle("100", "110", "95", "105")
        assert is_bullish_candle(candle)

        candle = create_test_candle("105", "110", "95", "100")
        assert not is_bullish_candle(candle)

    def test_is_bearish_candle(self) -> None:
        """Test bearish candle detection."""
        candle = create_test_candle("105", "110", "95", "100")
        assert is_bearish_candle(candle)

        candle = create_test_candle("100", "110", "95", "105")
        assert not is_bearish_candle(candle)

    def test_compute_candle_body_size(self) -> None:
        """Test candle body size computation."""
        candle = create_test_candle("100", "110", "95", "105")
        assert compute_candle_body_size(candle) == Decimal("5")

        candle = create_test_candle("105", "110", "95", "100")
        assert compute_candle_body_size(candle) == Decimal("5")

    def test_compute_candle_wick_sizes(self) -> None:
        """Test wick size computation."""
        candle = create_test_candle("100", "110", "90", "105")
        upper, lower = compute_candle_wick_sizes(candle)

        # Body: 100 to 105
        # Upper wick: 110 - 105 = 5
        # Lower wick: 100 - 90 = 10
        assert upper == Decimal("5")
        assert lower == Decimal("10")

    def test_compute_candle_range(self) -> None:
        """Test candle range computation."""
        candle = create_test_candle("100", "110", "90", "105")
        assert compute_candle_range(candle) == Decimal("20")
