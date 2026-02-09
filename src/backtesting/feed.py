"""Market data feed for backtesting.

Provides:
- Historical data loading from files or database
- Event iteration in chronological order
- Multi-symbol support
- Filtering by time range and data types
"""

import json
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path
from typing import Any

from src.types import CandleData, DataType, TickData, TradeData


def load_candles_from_jsonl(
    file_path: Path,
    symbol: str | None = None,
    start_time_ms: int | None = None,
    end_time_ms: int | None = None,
) -> list[CandleData]:
    """Load candle data from JSONL file.

    Args:
        file_path: Path to JSONL file.
        symbol: Optional symbol filter.
        start_time_ms: Optional start time.
        end_time_ms: Optional end time.

    Returns:
        List of candle records.
    """
    candles: list[CandleData] = []

    with open(file_path) as f:
        for line in f:
            if not line.strip():
                continue

            record = json.loads(line)

            if record.get("type") != "candle":
                continue

            data = record.get("data", {})
            if not data:
                continue

            # Apply filters
            if symbol and data.get("symbol") != symbol:
                continue

            open_time = data.get("open_time_ms", 0)
            if start_time_ms and open_time < start_time_ms:
                continue
            if end_time_ms and open_time > end_time_ms:
                continue

            # Convert to CandleData
            candle: CandleData = {
                "schema_version": data.get("schema_version", "1.0.0"),
                "provider": data.get("provider", "unknown"),
                "symbol": data["symbol"],
                "interval": data.get("interval", "1m"),
                "open_time_ms": open_time,
                "close_time_ms": data.get("close_time_ms", open_time),
                "open": Decimal(str(data.get("open", "0"))),
                "high": Decimal(str(data.get("high", "0"))),
                "low": Decimal(str(data.get("low", "0"))),
                "close": Decimal(str(data.get("close", "0"))),
                "volume": Decimal(str(data.get("volume", "0"))),
                "is_closed": data.get("is_closed", True),
                "raw": data.get("raw", {}),
            }

            candles.append(candle)

    # Sort by time
    candles.sort(key=lambda c: c["open_time_ms"])

    return candles


def load_trades_from_jsonl(
    file_path: Path,
    symbol: str | None = None,
    start_time_ms: int | None = None,
    end_time_ms: int | None = None,
) -> list[TradeData]:
    """Load trade data from JSONL file.

    Args:
        file_path: Path to JSONL file.
        symbol: Optional symbol filter.
        start_time_ms: Optional start time.
        end_time_ms: Optional end time.

    Returns:
        List of trade records.
    """
    trades: list[TradeData] = []

    with open(file_path) as f:
        for line in f:
            if not line.strip():
                continue

            record = json.loads(line)

            if record.get("type") != "trade":
                continue

            data = record.get("data", {})
            if not data:
                continue

            # Apply filters
            if symbol and data.get("symbol") != symbol:
                continue

            timestamp = data.get("timestamp_ms", 0)
            if start_time_ms and timestamp < start_time_ms:
                continue
            if end_time_ms and timestamp > end_time_ms:
                continue

            trade: TradeData = {
                "schema_version": data.get("schema_version", "1.0.0"),
                "provider": data.get("provider", "unknown"),
                "symbol": data["symbol"],
                "trade_id": data.get("trade_id", str(timestamp)),
                "timestamp_ms": timestamp,
                "price": Decimal(str(data.get("price", "0"))),
                "quantity": Decimal(str(data.get("quantity", "0"))),
                "side": data.get("side", "buy"),
                "raw": data.get("raw", {}),
            }

            trades.append(trade)

    trades.sort(key=lambda t: t["timestamp_ms"])

    return trades


class MarketDataFeed:
    """Market data feed for backtesting.

    Provides chronologically ordered events from historical data.

    Input: Historical data files or in-memory records.
    Output: Iterator of market events (candles, trades, ticks).
    """

    def __init__(
        self,
        candles: list[CandleData] | None = None,
        trades: list[TradeData] | None = None,
        ticks: list[TickData] | None = None,
    ):
        """Initialize market data feed.

        Args:
            candles: List of candle records.
            trades: List of trade records.
            ticks: List of tick records.
        """
        self.candles = candles or []
        self.trades = trades or []
        self.ticks = ticks or []

        # Merge and sort all events
        self._events: list[tuple[int, str, Any]] = []
        self._build_events()

    def _build_events(self) -> None:
        """Build chronologically sorted event stream.

        Side effects: Populates _events list.
        """
        events: list[tuple[int, str, CandleData | TradeData | TickData]] = []

        for candle in self.candles:
            events.append((candle["open_time_ms"], "candle", candle))

        for trade in self.trades:
            events.append((trade["timestamp_ms"], "trade", trade))

        for tick in self.ticks:
            events.append((tick["timestamp_ms"], "tick", tick))

        # Sort by timestamp
        events.sort(key=lambda e: e[0])

        self._events = events

    def __iter__(self) -> Iterator[tuple[str, Any]]:
        """Iterate over events in chronological order.

        Yields:
            Tuples of (event_type, event_data).
        """
        for _timestamp, event_type, data in self._events:
            yield event_type, data

    def get_candles(self, symbol: str | None = None) -> list[CandleData]:
        """Get all candles, optionally filtered by symbol.

        Args:
            symbol: Optional symbol filter.

        Returns:
            List of candles.
        """
        if symbol:
            return [c for c in self.candles if c["symbol"] == symbol]
        return self.candles.copy()

    def get_trades(self, symbol: str | None = None) -> list[TradeData]:
        """Get all trades, optionally filtered by symbol.

        Args:
            symbol: Optional symbol filter.

        Returns:
            List of trades.
        """
        if symbol:
            return [t for t in self.trades if t["symbol"] == symbol]
        return self.trades.copy()

    def get_time_range(self) -> tuple[int, int] | None:
        """Get time range of data.

        Returns:
            Tuple of (start_time_ms, end_time_ms) or None if empty.
        """
        if not self._events:
            return None

        return self._events[0][0], self._events[-1][0]


def create_feed_from_file(
    file_path: Path,
    symbols: list[str] | None = None,
    start_time_ms: int | None = None,
    end_time_ms: int | None = None,
    data_types: list[DataType] | None = None,
) -> MarketDataFeed:
    """Create market data feed from JSONL file.

    Args:
        file_path: Path to JSONL file.
        symbols: Optional list of symbols to load.
        start_time_ms: Optional start time filter.
        end_time_ms: Optional end time filter.
        data_types: Optional list of data types to load.

    Returns:
        MarketDataFeed instance.
    """
    load_candles = not data_types or "candle" in data_types
    load_trades = not data_types or "trade" in data_types

    candles = []
    trades = []
    ticks: list[TickData] = []

    if load_candles:
        for symbol in symbols or [""]:
            candles.extend(load_candles_from_jsonl(file_path, symbol, start_time_ms, end_time_ms))

    if load_trades:
        for symbol in symbols or [""]:
            trades.extend(load_trades_from_jsonl(file_path, symbol, start_time_ms, end_time_ms))

    # TODO: load_ticks_from_jsonl if needed

    return MarketDataFeed(candles=candles, trades=trades, ticks=ticks)


def create_feed_from_candles(candles: list[CandleData]) -> MarketDataFeed:
    """Create feed from pre-loaded candle data.

    Args:
        candles: List of candle records.

    Returns:
        MarketDataFeed instance.
    """
    return MarketDataFeed(candles=candles)


def create_feed_from_trades(trades: list[TradeData]) -> MarketDataFeed:
    """Create feed from pre-loaded trade data.

    Args:
        trades: List of trade records.

    Returns:
        MarketDataFeed instance.
    """
    return MarketDataFeed(trades=trades)
