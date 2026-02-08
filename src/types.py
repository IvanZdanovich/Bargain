"""
Centralized type definitions for the Bargain trading framework.

All TypedDict and Callable aliases live here as the single source of truth.
"""

from typing import TypedDict, Callable, Literal, Sequence, Any, Awaitable
from decimal import Decimal

# Note: SCHEMA_VERSION is now centralized in src/config.py and configs/default.yaml

# === Enums as Literals ===
Side = Literal["buy", "sell"]
DataType = Literal["trade", "orderbook_snapshot", "orderbook_delta", "candle", "tick"]
ProviderStatus = Literal["disconnected", "connecting", "connected", "error", "rate_limited"]
OperationMode = Literal["live", "historical", "replay"]

# === Core Market Data Structures ===


class TradeData(TypedDict):
    """Normalized trade record."""
    schema_version: str
    provider: str
    symbol: str
    trade_id: str
    timestamp_ms: int
    price: Decimal
    quantity: Decimal
    side: Side
    raw: dict[str, Any]


class OrderBookLevelData(TypedDict):
    """Single price level in order book."""
    price: Decimal
    quantity: Decimal


class OrderBookSnapshotData(TypedDict):
    """Full order book snapshot."""
    schema_version: str
    provider: str
    symbol: str
    timestamp_ms: int
    sequence: int
    bids: Sequence[OrderBookLevelData]
    asks: Sequence[OrderBookLevelData]
    raw: dict[str, Any]


class OrderBookDeltaData(TypedDict):
    """Incremental order book update."""
    schema_version: str
    provider: str
    symbol: str
    timestamp_ms: int
    sequence: int
    bid_updates: Sequence[OrderBookLevelData]
    ask_updates: Sequence[OrderBookLevelData]
    raw: dict[str, Any]


class CandleData(TypedDict):
    """OHLCV candle record."""
    schema_version: str
    provider: str
    symbol: str
    interval: str  # "1m", "5m", "1h", etc.
    open_time_ms: int
    close_time_ms: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    is_closed: bool
    raw: dict[str, Any]


class TickData(TypedDict):
    """Unified tick (best bid/ask + last trade)."""
    schema_version: str
    provider: str
    symbol: str
    timestamp_ms: int
    bid_price: Decimal
    bid_quantity: Decimal
    ask_price: Decimal
    ask_quantity: Decimal
    last_price: Decimal
    last_quantity: Decimal
    raw: dict[str, Any]


# === Configuration Types ===


class SubscriptionConfigData(TypedDict):
    """Subscription request configuration."""
    symbol: str
    data_types: Sequence[DataType]
    interval: str | None  # For candles


class ProviderConfigData(TypedDict):
    """Provider initialization configuration."""
    name: str
    api_key: str | None
    api_secret: str | None
    testnet: bool
    rate_limit_per_second: int
    reconnect_attempts: int
    reconnect_delay_ms: int


class HistoricalRequestData(TypedDict):
    """Historical data fetch request."""
    symbol: str
    data_type: DataType
    start_time_ms: int
    end_time_ms: int
    interval: str | None
    limit: int | None


# === Event Types ===

MarketDataRecord = TradeData | CandleData | TickData | OrderBookSnapshotData | OrderBookDeltaData


class MarketEventData(TypedDict):
    """Unified market event wrapper for event bus."""
    event_type: DataType
    provider: str
    symbol: str
    timestamp_ms: int
    data: MarketDataRecord


class ErrorEventData(TypedDict):
    """Error event for event bus."""
    provider: str
    error_type: str
    message: str
    timestamp_ms: int
    recoverable: bool


class StatusEventData(TypedDict):
    """Provider status change event."""
    provider: str
    old_status: ProviderStatus
    new_status: ProviderStatus
    timestamp_ms: int


# === Callback Types (Handler Functions) ===

TradeHandlerFn = Callable[[TradeData], None]
OrderBookSnapshotHandlerFn = Callable[[OrderBookSnapshotData], None]
OrderBookDeltaHandlerFn = Callable[[OrderBookDeltaData], None]
CandleHandlerFn = Callable[[CandleData], None]
TickHandlerFn = Callable[[TickData], None]
ErrorHandlerFn = Callable[[str, Exception], None]
StatusHandlerFn = Callable[[str, ProviderStatus], None]

# Async variants
AsyncTradeHandlerFn = Callable[[TradeData], Awaitable[None]]
AsyncCandleHandlerFn = Callable[[CandleData], Awaitable[None]]


class HandlersData(TypedDict, total=False):
    """Event handler callbacks for Data Controller."""
    on_trade: TradeHandlerFn
    on_orderbook_snapshot: OrderBookSnapshotHandlerFn
    on_orderbook_delta: OrderBookDeltaHandlerFn
    on_candle: CandleHandlerFn
    on_tick: TickHandlerFn
    on_error: ErrorHandlerFn
    on_status_change: StatusHandlerFn


# === Event Bus Types ===

EventEmitFn = Callable[[str, dict[str, Any]], None]
AsyncEventEmitFn = Callable[[str, dict[str, Any]], Awaitable[None]]
EventSubscribeFn = Callable[[str, Callable[[dict[str, Any]], None]], Callable[[], None]]


class EventBusConfigData(TypedDict, total=False):
    """Event bus configuration."""
    emit: EventEmitFn
    async_emit: AsyncEventEmitFn
    subscribe: EventSubscribeFn


# === Storage Types ===

StorageWriteFn = Callable[[MarketDataRecord], Awaitable[None]]
StorageBatchWriteFn = Callable[[Sequence[MarketDataRecord]], Awaitable[None]]


class StorageConfigData(TypedDict, total=False):
    """Storage layer configuration."""
    write: StorageWriteFn
    batch_write: StorageBatchWriteFn
    enabled: bool
    batch_size: int
    flush_interval_ms: int


# === Provider Interface Types ===

ParseTradeFn = Callable[[dict[str, Any], str], TradeData]
ParseCandleFn = Callable[[dict[str, Any], str], CandleData]
ParseOrderBookSnapshotFn = Callable[[dict[str, Any], str, str], OrderBookSnapshotData]
ParseTickFn = Callable[[dict[str, Any], str], TickData]


# === Rate Limiter State ===


class RateLimiterStateData(TypedDict):
    """Token bucket rate limiter state."""
    tokens: float
    max_tokens: int
    last_refill: float
    refill_rate: int


# === Health Check Types ===


class ProviderHealthData(TypedDict):
    """Provider health status."""
    provider: str
    status: ProviderStatus
    last_message_ms: int | None
    message_count: int
    error_count: int
    reconnect_count: int
    latency_ms: float | None

