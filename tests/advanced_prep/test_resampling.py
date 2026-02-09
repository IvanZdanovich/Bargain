"""
Tests for resampling functionality.
"""

from decimal import Decimal

import pytest

from src.advanced_prep.resampling import CandleResampler, format_timeframe, parse_timeframe_to_ms
from src.types import TickData


class TestCandleResampler:
    """Tests for CandleResampler class."""

    def test_init(self) -> None:
        """Test initialization."""
        resampler = CandleResampler(60000)  # 1 minute
        assert resampler._timeframe_ms == 60000

    def test_init_invalid(self) -> None:
        """Test initialization with invalid timeframe."""
        with pytest.raises(ValueError):
            CandleResampler(0)
        with pytest.raises(ValueError):
            CandleResampler(-1000)

    def test_single_tick(self) -> None:
        """Test processing single tick."""
        resampler = CandleResampler(60000)

        tick: TickData = {
            "schema_version": "1.0",
            "provider": "test",
            "symbol": "BTCUSDT",
            "timestamp_ms": 1000000,
            "bid_price": Decimal("50000"),
            "bid_quantity": Decimal("1"),
            "ask_price": Decimal("50001"),
            "ask_quantity": Decimal("1"),
            "last_price": Decimal("50000"),
            "last_quantity": Decimal("0.5"),
            "raw": {},
        }

        result = resampler.update_tick(tick)
        assert result is None  # First tick doesn't finalize anything

        current = resampler.get_current_candle()
        assert current is not None
        assert current["open"] == Decimal("50000")
        assert current["high"] == Decimal("50000")
        assert current["low"] == Decimal("50000")
        assert current["close"] == Decimal("50000")
        assert current["volume"] == Decimal("0.5")

    def test_multiple_ticks_same_candle(self) -> None:
        """Test processing multiple ticks in same candle."""
        resampler = CandleResampler(60000)

        # Tick 1
        tick1: TickData = {
            "schema_version": "1.0",
            "provider": "test",
            "symbol": "BTCUSDT",
            "timestamp_ms": 60000,  # 00:01:00
            "bid_price": Decimal("50000"),
            "bid_quantity": Decimal("1"),
            "ask_price": Decimal("50001"),
            "ask_quantity": Decimal("1"),
            "last_price": Decimal("50000"),
            "last_quantity": Decimal("1"),
            "raw": {},
        }

        resampler.update_tick(tick1)

        # Tick 2 - higher price
        tick2 = tick1.copy()
        tick2["timestamp_ms"] = 61000
        tick2["last_price"] = Decimal("50100")
        tick2["last_quantity"] = Decimal("2")

        resampler.update_tick(tick2)

        # Tick 3 - lower price
        tick3 = tick1.copy()
        tick3["timestamp_ms"] = 62000
        tick3["last_price"] = Decimal("49900")
        tick3["last_quantity"] = Decimal("1.5")

        resampler.update_tick(tick3)

        current = resampler.get_current_candle()
        assert current is not None
        assert current["open"] == Decimal("50000")
        assert current["high"] == Decimal("50100")
        assert current["low"] == Decimal("49900")
        assert current["close"] == Decimal("49900")
        assert current["volume"] == Decimal("4.5")

    def test_candle_finalization(self) -> None:
        """Test candle finalization on timeframe boundary."""
        resampler = CandleResampler(60000)

        # First candle
        tick1: TickData = {
            "schema_version": "1.0",
            "provider": "test",
            "symbol": "BTCUSDT",
            "timestamp_ms": 60000,
            "bid_price": Decimal("50000"),
            "bid_quantity": Decimal("1"),
            "ask_price": Decimal("50001"),
            "ask_quantity": Decimal("1"),
            "last_price": Decimal("50000"),
            "last_quantity": Decimal("1"),
            "raw": {},
        }

        resampler.update_tick(tick1)

        # Cross boundary
        tick2 = tick1.copy()
        tick2["timestamp_ms"] = 120000  # Next minute
        tick2["last_price"] = Decimal("50100")

        finalized = resampler.update_tick(tick2)

        assert finalized is not None
        assert finalized["is_finalized"] is True
        assert finalized["open"] == Decimal("50000")
        assert finalized["close"] == Decimal("50000")

    def test_vwap_calculation(self) -> None:
        """Test VWAP calculation."""
        resampler = CandleResampler(60000)

        tick1: TickData = {
            "schema_version": "1.0",
            "provider": "test",
            "symbol": "BTCUSDT",
            "timestamp_ms": 60000,
            "bid_price": Decimal("100"),
            "bid_quantity": Decimal("1"),
            "ask_price": Decimal("101"),
            "ask_quantity": Decimal("1"),
            "last_price": Decimal("100"),
            "last_quantity": Decimal("10"),
            "raw": {},
        }

        resampler.update_tick(tick1)

        tick2 = tick1.copy()
        tick2["timestamp_ms"] = 61000
        tick2["last_price"] = Decimal("200")
        tick2["last_quantity"] = Decimal("5")

        resampler.update_tick(tick2)

        current = resampler.get_current_candle()
        # VWAP = (100*10 + 200*5) / (10+5) = 2000/15 = 133.333...
        assert current is not None
        expected_vwap = (Decimal("100") * Decimal("10") + Decimal("200") * Decimal("5")) / Decimal(
            "15"
        )
        assert abs(current["vwap"] - expected_vwap) < Decimal("0.001")

    def test_reset(self) -> None:
        """Test reset functionality."""
        resampler = CandleResampler(60000)

        tick: TickData = {
            "schema_version": "1.0",
            "provider": "test",
            "symbol": "BTCUSDT",
            "timestamp_ms": 60000,
            "bid_price": Decimal("50000"),
            "bid_quantity": Decimal("1"),
            "ask_price": Decimal("50001"),
            "ask_quantity": Decimal("1"),
            "last_price": Decimal("50000"),
            "last_quantity": Decimal("1"),
            "raw": {},
        }

        resampler.update_tick(tick)
        resampler.reset()

        assert resampler.get_current_candle() is None


class TestTimeframeUtils:
    """Tests for timeframe parsing and formatting."""

    def test_parse_timeframe_to_ms(self) -> None:
        """Test parsing timeframe strings."""
        assert parse_timeframe_to_ms("1s") == 1000
        assert parse_timeframe_to_ms("1m") == 60000
        assert parse_timeframe_to_ms("5m") == 300000
        assert parse_timeframe_to_ms("1h") == 3600000
        assert parse_timeframe_to_ms("1d") == 86400000

    def test_parse_timeframe_invalid(self) -> None:
        """Test parsing invalid timeframe strings."""
        with pytest.raises(ValueError):
            parse_timeframe_to_ms("")

        with pytest.raises(ValueError):
            parse_timeframe_to_ms("5x")

        with pytest.raises(ValueError):
            parse_timeframe_to_ms("abc")

        with pytest.raises(ValueError):
            parse_timeframe_to_ms("-5m")

    def test_format_timeframe(self) -> None:
        """Test formatting milliseconds to timeframe strings."""
        assert format_timeframe(1000) == "1s"
        assert format_timeframe(60000) == "1m"
        assert format_timeframe(300000) == "5m"
        assert format_timeframe(3600000) == "1h"
        assert format_timeframe(86400000) == "1d"
