"""
Tests for indicator computations.
"""

from decimal import Decimal

from src.advanced_prep.indicators import (
    compute_atr_batch,
    compute_ema,
    compute_log_return,
    compute_percentage_change,
    compute_rolling_volatility,
    compute_sma,
    compute_true_range,
    compute_vwap_batch,
    compute_wma,
    init_atr_state,
    init_ema_state,
    update_atr_streaming,
    update_ema_streaming,
)


class TestSMA:
    """Tests for Simple Moving Average."""

    def test_compute_sma(self) -> None:
        """Test SMA computation."""
        values = [Decimal(str(x)) for x in [10, 20, 30, 40, 50]]
        result = compute_sma(values, 3)

        assert len(result) == 3
        assert result[0] == Decimal("20")
        assert result[1] == Decimal("30")
        assert result[2] == Decimal("40")

    def test_compute_sma_edge_cases(self) -> None:
        """Test SMA edge cases."""
        values = [Decimal(str(x)) for x in [10, 20, 30]]

        assert compute_sma(values, 0) == []
        assert compute_sma(values, 5) == []
        assert len(compute_sma(values, 3)) == 1


class TestEMA:
    """Tests for Exponential Moving Average."""

    def test_compute_ema(self) -> None:
        """Test EMA computation."""
        values = [Decimal(str(x)) for x in [10, 20, 30, 40, 50]]
        result = compute_ema(values, 3)

        assert len(result) == 5
        assert result[0] == Decimal("10")  # First value
        # Subsequent values should trend toward recent prices

    def test_ema_streaming(self) -> None:
        """Test streaming EMA updates."""
        state = init_ema_state(3, Decimal("10"))

        assert state.value == Decimal("10")
        assert state.period == 3
        assert state.initialized

        state = update_ema_streaming(state, Decimal("20"))
        # alpha = 2/(3+1) = 0.5
        # new_ema = 0.5 * 20 + 0.5 * 10 = 15
        assert state.value == Decimal("15")

        state = update_ema_streaming(state, Decimal("30"))
        # new_ema = 0.5 * 30 + 0.5 * 15 = 22.5
        assert state.value == Decimal("22.5")


class TestWMA:
    """Tests for Weighted Moving Average."""

    def test_compute_wma(self) -> None:
        """Test WMA computation."""
        values = [Decimal(str(x)) for x in [10, 20, 30, 40, 50]]
        result = compute_wma(values, 3)

        assert len(result) == 3
        # WMA of [10, 20, 30] with weights [1, 2, 3]
        # = (10*1 + 20*2 + 30*3) / (1+2+3) = 140/6 = 23.333...
        expected = (Decimal("10") + Decimal("20") * 2 + Decimal("30") * 3) / 6
        assert abs(result[0] - expected) < Decimal("0.001")


class TestVWAP:
    """Tests for Volume Weighted Average Price."""

    def test_compute_vwap_batch(self) -> None:
        """Test VWAP batch computation."""
        prices = [Decimal(str(x)) for x in [100, 200, 300]]
        volumes = [Decimal(str(x)) for x in [10, 5, 2]]

        result = compute_vwap_batch(prices, volumes)

        assert len(result) == 3
        # First: 100*10 / 10 = 100
        assert result[0] == Decimal("100")
        # Second: (100*10 + 200*5) / (10+5) = 2000/15 = 133.333...
        expected = (Decimal("100") * 10 + Decimal("200") * 5) / 15
        assert abs(result[1] - expected) < Decimal("0.001")

    def test_compute_vwap_mismatched_lengths(self) -> None:
        """Test VWAP with mismatched input lengths."""
        prices = [Decimal("100"), Decimal("200")]
        volumes = [Decimal("10")]

        result = compute_vwap_batch(prices, volumes)
        assert result == []


class TestATR:
    """Tests for Average True Range."""

    def test_compute_true_range(self) -> None:
        """Test True Range computation."""
        # No previous close
        tr = compute_true_range(Decimal("110"), Decimal("90"), None)
        assert tr == Decimal("20")

        # With previous close
        tr = compute_true_range(Decimal("110"), Decimal("95"), Decimal("100"))
        # TR = max(110-95, |110-100|, |95-100|) = max(15, 10, 5) = 15
        assert tr == Decimal("15")

    def test_compute_atr_batch(self) -> None:
        """Test ATR batch computation."""
        highs = [Decimal(str(x)) for x in [110, 120, 115]]
        lows = [Decimal(str(x)) for x in [90, 95, 92]]
        closes = [Decimal(str(x)) for x in [100, 110, 105]]

        result = compute_atr_batch(highs, lows, closes, 2)

        assert len(result) == 2
        # TR[0] = 110-90 = 20
        # TR[1] = max(120-95, |120-100|, |95-100|) = max(25, 20, 5) = 25
        # TR[2] = max(115-92, |115-110|, |92-110|) = max(23, 5, 18) = 23
        # ATR[0] = (20 + 25) / 2 = 22.5
        # ATR[1] = (25 + 23) / 2 = 24
        assert result[0] == Decimal("22.5")
        assert result[1] == Decimal("24")

    def test_atr_streaming(self) -> None:
        """Test streaming ATR updates."""
        state = init_atr_state(2)

        state = update_atr_streaming(state, Decimal("110"), Decimal("90"), Decimal("100"))
        state = update_atr_streaming(state, Decimal("120"), Decimal("95"), Decimal("110"))

        # After 2 periods, window should be full
        assert state.tr_window.is_full()
        assert state.value > Decimal(0)


class TestVolatility:
    """Tests for volatility indicators."""

    def test_compute_rolling_volatility(self) -> None:
        """Test rolling volatility computation."""
        returns = [Decimal(str(x)) for x in [0.01, -0.01, 0.02, -0.02, 0.01]]
        result = compute_rolling_volatility(returns, 3)

        assert len(result) == 3
        # Each result should be positive
        assert all(v >= 0 for v in result)


class TestHelpers:
    """Tests for helper functions."""

    def test_compute_percentage_change(self) -> None:
        """Test percentage change computation."""
        result = compute_percentage_change(Decimal("110"), Decimal("100"))
        assert result == Decimal("10")

        result = compute_percentage_change(Decimal("90"), Decimal("100"))
        assert result == Decimal("-10")

        # Zero previous
        result = compute_percentage_change(Decimal("100"), Decimal("0"))
        assert result == Decimal("0")

    def test_compute_log_return(self) -> None:
        """Test log return computation."""
        result = compute_log_return(Decimal("110"), Decimal("100"))
        # ln(110/100) = ln(1.1) ≈ 0.0953
        assert abs(result - Decimal("0.0953")) < Decimal("0.001")

        # Zero values
        result = compute_log_return(Decimal("0"), Decimal("100"))
        assert result == Decimal("0")

        result = compute_log_return(Decimal("100"), Decimal("0"))
        assert result == Decimal("0")
