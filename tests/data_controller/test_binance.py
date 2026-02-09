"""Unit tests for Binance provider parsing functions."""

from decimal import Decimal

import pytest

from src.config import get_schema_version
from src.data_controller.providers.binance import (
    create_binance_provider,
    parse_binance_candle,
    parse_binance_candle_rest,
    parse_binance_orderbook_snapshot,
    parse_binance_ticker,
    parse_binance_trade,
)


@pytest.fixture
def binance_config():
    """Create test Binance provider config."""
    return {
        "name": "binance",
        "api_key": None,
        "api_secret": None,
        "testnet": False,
        "rate_limit_per_second": 10,
        "reconnect_attempts": 3,
        "reconnect_delay_ms": 1000,
    }


@pytest.fixture
def raw_binance_trade():
    """Raw Binance trade WebSocket message."""
    return {
        "e": "trade",
        "E": 1672531200000,
        "s": "BTCUSDT",
        "t": 123456789,
        "p": "42000.50",
        "q": "0.5",
        "T": 1672531200000,
        "m": False,  # buyer is taker
    }


@pytest.fixture
def raw_binance_trade_seller():
    """Raw Binance trade where seller is taker."""
    return {
        "e": "trade",
        "E": 1672531200000,
        "s": "BTCUSDT",
        "t": 123456790,
        "p": "42001.00",
        "q": "1.0",
        "T": 1672531200001,
        "m": True,  # buyer is maker = sell
    }


@pytest.fixture
def raw_binance_kline():
    """Raw Binance kline WebSocket message."""
    return {
        "e": "kline",
        "E": 1672531200000,
        "s": "BTCUSDT",
        "k": {
            "t": 1672531140000,
            "T": 1672531199999,
            "s": "BTCUSDT",
            "i": "1m",
            "o": "42000.00",
            "h": "42100.00",
            "l": "41900.00",
            "c": "42050.00",
            "v": "100.5",
            "x": True,
        },
    }


@pytest.fixture
def raw_binance_kline_open():
    """Raw Binance kline that is not yet closed."""
    return {
        "e": "kline",
        "E": 1672531200000,
        "s": "ETHUSDT",
        "k": {
            "t": 1672531140000,
            "T": 1672531199999,
            "s": "ETHUSDT",
            "i": "5m",
            "o": "1500.00",
            "h": "1520.00",
            "l": "1490.00",
            "c": "1510.00",
            "v": "500.0",
            "x": False,
        },
    }


@pytest.fixture
def raw_binance_rest_kline():
    """Raw Binance REST API kline response."""
    return [
        1672531140000,  # open time
        "42000.00",  # open
        "42100.00",  # high
        "41900.00",  # low
        "42050.00",  # close
        "100.5",  # volume
        1672531199999,  # close time
        "4220000.00",  # quote asset volume
        150,  # number of trades
        "50.0",  # taker buy base
        "2100000.00",  # taker buy quote
        "0",  # ignore
    ]


@pytest.fixture
def raw_binance_depth():
    """Raw Binance depth REST response."""
    return {
        "lastUpdateId": 123456789,
        "E": 1672531200000,
        "bids": [
            ["42000.00", "1.5"],
            ["41999.00", "2.0"],
            ["41998.00", "0.5"],
        ],
        "asks": [
            ["42001.00", "1.0"],
            ["42002.00", "2.5"],
            ["42003.00", "1.2"],
        ],
    }


@pytest.fixture
def raw_binance_ticker():
    """Raw Binance 24hr ticker."""
    return {
        "e": "24hrTicker",
        "E": 1672531200000,
        "s": "BTCUSDT",
        "b": "42000.00",
        "B": "1.5",
        "a": "42001.00",
        "A": "2.0",
        "c": "42000.50",
        "Q": "0.5",
    }


class TestParseBinanceTrade:
    """Tests for parse_binance_trade function."""

    def test_parse_buy_trade(self, raw_binance_trade):
        """Parse trade where buyer is taker."""
        result = parse_binance_trade(raw_binance_trade, "binance")

        assert result["schema_version"] == get_schema_version()
        assert result["provider"] == "binance"
        assert result["symbol"] == "BTC/USDT"
        assert result["trade_id"] == "123456789"
        assert result["price"] == Decimal("42000.50")
        assert result["quantity"] == Decimal("0.5")
        assert result["side"] == "buy"
        assert result["timestamp_ms"] == 1672531200000
        assert result["raw"] == raw_binance_trade

    def test_parse_sell_trade(self, raw_binance_trade_seller):
        """Parse trade where seller is taker."""
        result = parse_binance_trade(raw_binance_trade_seller, "binance")

        assert result["side"] == "sell"
        assert result["price"] == Decimal("42001.00")
        assert result["quantity"] == Decimal("1.0")

    def test_different_provider_name(self, raw_binance_trade):
        """Use custom provider name."""
        result = parse_binance_trade(raw_binance_trade, "binance_testnet")
        assert result["provider"] == "binance_testnet"


class TestParseBinanceCandle:
    """Tests for parse_binance_candle function."""

    def test_parse_closed_candle(self, raw_binance_kline):
        """Parse closed candle."""
        result = parse_binance_candle(raw_binance_kline, "binance")

        assert result["schema_version"] == get_schema_version()
        assert result["provider"] == "binance"
        assert result["symbol"] == "BTC/USDT"
        assert result["interval"] == "1m"
        assert result["open_time_ms"] == 1672531140000
        assert result["close_time_ms"] == 1672531199999
        assert result["open"] == Decimal("42000.00")
        assert result["high"] == Decimal("42100.00")
        assert result["low"] == Decimal("41900.00")
        assert result["close"] == Decimal("42050.00")
        assert result["volume"] == Decimal("100.5")
        assert result["is_closed"] is True

    def test_parse_open_candle(self, raw_binance_kline_open):
        """Parse open (incomplete) candle."""
        result = parse_binance_candle(raw_binance_kline_open, "binance")

        assert result["symbol"] == "ETH/USDT"
        assert result["interval"] == "5m"
        assert result["is_closed"] is False


class TestParseBinanceCandleRest:
    """Tests for parse_binance_candle_rest function."""

    def test_parse_rest_kline(self, raw_binance_rest_kline):
        """Parse REST API kline response."""
        result = parse_binance_candle_rest(
            raw_binance_rest_kline,
            "BTCUSDT",
            "1m",
            "binance",
        )

        assert result["schema_version"] == get_schema_version()
        assert result["symbol"] == "BTC/USDT"
        assert result["interval"] == "1m"
        assert result["open"] == Decimal("42000.00")
        assert result["high"] == Decimal("42100.00")
        assert result["low"] == Decimal("41900.00")
        assert result["close"] == Decimal("42050.00")
        assert result["volume"] == Decimal("100.5")
        assert result["is_closed"] is True


class TestParseBinanceOrderbookSnapshot:
    """Tests for parse_binance_orderbook_snapshot function."""

    def test_parse_depth(self, raw_binance_depth):
        """Parse order book depth snapshot."""
        result = parse_binance_orderbook_snapshot(
            raw_binance_depth,
            "BTCUSDT",
            "binance",
        )

        assert result["schema_version"] == get_schema_version()
        assert result["symbol"] == "BTC/USDT"
        assert result["sequence"] == 123456789
        assert len(result["bids"]) == 3
        assert len(result["asks"]) == 3

        # Check first bid
        assert result["bids"][0]["price"] == Decimal("42000.00")
        assert result["bids"][0]["quantity"] == Decimal("1.5")

        # Check first ask
        assert result["asks"][0]["price"] == Decimal("42001.00")
        assert result["asks"][0]["quantity"] == Decimal("1.0")


class TestParseBinanceTicker:
    """Tests for parse_binance_ticker function."""

    def test_parse_ticker(self, raw_binance_ticker):
        """Parse 24hr ticker."""
        result = parse_binance_ticker(raw_binance_ticker, "binance")

        assert result["schema_version"] == get_schema_version()
        assert result["symbol"] == "BTC/USDT"
        assert result["bid_price"] == Decimal("42000.00")
        assert result["bid_quantity"] == Decimal("1.5")
        assert result["ask_price"] == Decimal("42001.00")
        assert result["ask_quantity"] == Decimal("2.0")
        assert result["last_price"] == Decimal("42000.50")
        assert result["last_quantity"] == Decimal("0.5")


class TestCreateBinanceProvider:
    """Tests for create_binance_provider function."""

    def test_create_provider_state(self, binance_config):
        """Create provider state with all required fields."""
        state = create_binance_provider(binance_config)

        assert state["name"] == "binance"
        assert state["status"] == "disconnected"
        assert state["config"] == binance_config
        assert state["ws_session"] is None
        assert state["http_session"] is None
        assert state["subscriptions"] == []
        assert state["message_count"] == 0
        assert state["error_count"] == 0
        assert state["reconnect_count"] == 0
        assert "rate_limiter" in state

    def test_rate_limiter_initialized(self, binance_config):
        """Rate limiter initialized from config."""
        state = create_binance_provider(binance_config)

        rate_limiter = state["rate_limiter"]
        assert rate_limiter["max_tokens"] == 10
        assert rate_limiter["refill_rate"] == 10
