"""Unit tests for normalization functions."""

import pytest
from decimal import Decimal

from src.data_controller.normalization import (
    to_decimal,
    normalize_side,
    normalize_symbol,
    denormalize_symbol,
    validate_timestamp,
    validate_sequence,
    validate_price,
    validate_quantity,
    validate_orderbook_integrity,
)


class TestToDecimal:
    """Tests for to_decimal function."""

    def test_string_conversion(self):
        """Convert string to Decimal."""
        assert to_decimal("123.456") == Decimal("123.456")

    def test_integer_conversion(self):
        """Convert integer to Decimal."""
        assert to_decimal(100) == Decimal("100")

    def test_float_conversion(self):
        """Convert float to Decimal."""
        result = to_decimal(0.1)
        assert result == Decimal("0.1")

    def test_negative_value(self):
        """Convert negative value."""
        assert to_decimal("-50.5") == Decimal("-50.5")

    def test_scientific_notation(self):
        """Convert scientific notation string."""
        assert to_decimal("1e-8") == Decimal("1e-8")

    def test_invalid_value_raises(self):
        """Raise ValueError for invalid input."""
        with pytest.raises(ValueError):
            to_decimal("not_a_number")

    def test_empty_string_raises(self):
        """Raise ValueError for empty string."""
        with pytest.raises(ValueError):
            to_decimal("")


class TestNormalizeSide:
    """Tests for normalize_side function."""

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("buy", "buy"),
            ("BUY", "buy"),
            ("bid", "buy"),
            ("b", "buy"),
            ("long", "buy"),
            ("buyer", "buy"),
            ("sell", "sell"),
            ("SELL", "sell"),
            ("ask", "sell"),
            ("s", "sell"),
            ("short", "sell"),
            ("seller", "sell"),
        ],
    )
    def test_valid_sides(self, raw, expected):
        """Normalize various side representations."""
        assert normalize_side(raw) == expected

    def test_whitespace_handling(self):
        """Handle whitespace in input."""
        assert normalize_side("  buy  ") == "buy"

    def test_invalid_side_raises(self):
        """Raise ValueError for unknown side."""
        with pytest.raises(ValueError):
            normalize_side("unknown")


class TestNormalizeSymbol:
    """Tests for normalize_symbol function."""

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("BTCUSDT", "BTC/USDT"),
            ("btcusdt", "BTC/USDT"),
            ("ETH-USD", "ETH/USD"),
            ("SOL_USDC", "SOL/USDC"),
            ("BTC/USDT", "BTC/USDT"),
            ("ETHBTC", "ETH/BTC"),
            ("BNBETH", "BNB/ETH"),
            ("EURUSDT", "EUR/USDT"),
        ],
    )
    def test_symbol_normalization(self, raw, expected):
        """Normalize various symbol formats."""
        assert normalize_symbol(raw, "binance") == expected

    def test_unknown_quote_currency(self):
        """Return uppercase for unknown patterns."""
        result = normalize_symbol("ABCXYZ", "binance")
        assert result == "ABCXYZ"


class TestDenormalizeSymbol:
    """Tests for denormalize_symbol function."""

    def test_binance_format(self):
        """Convert to Binance format."""
        assert denormalize_symbol("BTC/USDT", "binance") == "BTCUSDT"

    def test_already_denormalized(self):
        """Handle already denormalized symbol."""
        assert denormalize_symbol("BTCUSDT", "binance") == "BTCUSDT"


class TestValidateTimestamp:
    """Tests for validate_timestamp function."""

    def test_valid_timestamp(self):
        """Accept valid recent timestamp."""
        # January 2024
        assert validate_timestamp(1704067200000) is True

    def test_too_old_timestamp(self):
        """Reject timestamp before 2020."""
        assert validate_timestamp(1000000000000) is False

    def test_future_timestamp(self):
        """Reject timestamp after 2100."""
        assert validate_timestamp(5000000000000) is False

    def test_boundary_2020(self):
        """Accept timestamp at 2020 boundary."""
        assert validate_timestamp(1577836800000) is True

    def test_current_time_valid(self):
        """Accept current time."""
        import time

        current_ms = int(time.time() * 1000)
        assert validate_timestamp(current_ms) is True


class TestValidateSequence:
    """Tests for validate_sequence function."""

    def test_first_message(self):
        """Accept first message without last sequence."""
        is_valid, gap = validate_sequence(100, None)
        assert is_valid is True
        assert gap is None

    def test_consecutive_sequence(self):
        """Accept consecutive sequence numbers."""
        is_valid, gap = validate_sequence(101, 100)
        assert is_valid is True
        assert gap is None

    def test_gap_detected(self):
        """Detect gap in sequence."""
        is_valid, gap = validate_sequence(105, 100)
        assert is_valid is False
        assert gap == 4

    def test_duplicate_detected(self):
        """Detect duplicate sequence number."""
        is_valid, gap = validate_sequence(100, 100)
        assert is_valid is False
        assert gap is None

    def test_out_of_order(self):
        """Detect out-of-order message."""
        is_valid, gap = validate_sequence(99, 100)
        assert is_valid is False
        assert gap is None


class TestValidatePrice:
    """Tests for validate_price function."""

    def test_valid_price(self):
        """Accept positive price."""
        assert validate_price(Decimal("100.50")) is True

    def test_zero_price(self):
        """Reject zero price."""
        assert validate_price(Decimal("0")) is False

    def test_negative_price(self):
        """Reject negative price."""
        assert validate_price(Decimal("-10")) is False


class TestValidateQuantity:
    """Tests for validate_quantity function."""

    def test_valid_quantity(self):
        """Accept positive quantity."""
        assert validate_quantity(Decimal("1.5")) is True

    def test_zero_quantity(self):
        """Reject zero quantity."""
        assert validate_quantity(Decimal("0")) is False


class TestValidateOrderbookIntegrity:
    """Tests for validate_orderbook_integrity function."""

    def test_valid_orderbook(self):
        """Accept valid order book."""
        bids = [(Decimal("100"), Decimal("1")), (Decimal("99"), Decimal("2"))]
        asks = [(Decimal("101"), Decimal("1")), (Decimal("102"), Decimal("2"))]
        is_valid, error = validate_orderbook_integrity(bids, asks)
        assert is_valid is True
        assert error is None

    def test_crossed_book(self):
        """Detect crossed order book."""
        bids = [(Decimal("101"), Decimal("1"))]
        asks = [(Decimal("100"), Decimal("1"))]
        is_valid, error = validate_orderbook_integrity(bids, asks)
        assert is_valid is False
        assert "Crossed book" in error

    def test_unsorted_bids(self):
        """Detect unsorted bids."""
        bids = [(Decimal("99"), Decimal("1")), (Decimal("100"), Decimal("2"))]
        asks = [(Decimal("101"), Decimal("1"))]
        is_valid, error = validate_orderbook_integrity(bids, asks)
        assert is_valid is False
        assert "Bids not sorted" in error

    def test_empty_book_valid(self):
        """Accept empty order book."""
        is_valid, error = validate_orderbook_integrity([], [])
        assert is_valid is True
