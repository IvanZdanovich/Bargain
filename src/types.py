"""
Centralized type definitions for the Bargain trading framework.

All TypedDict and Callable aliases live here as the single source of truth.
"""

from collections.abc import Awaitable, Callable, Sequence
from decimal import Decimal
from typing import Any, Literal, TypedDict

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


# === Advanced Data Preparation Types ===


class ResampledCandleData(TypedDict):
    """Resampled candle with OHLCV and VWAP."""

    open_time_ms: int
    close_time_ms: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    vwap: Decimal
    tick_count: int
    is_finalized: bool


class HeikenAshiData(TypedDict):
    """Heiken Ashi candle."""

    open_time_ms: int
    close_time_ms: int
    ha_open: Decimal
    ha_high: Decimal
    ha_low: Decimal
    ha_close: Decimal


class IndicatorStateData(TypedDict):
    """State for streaming indicator computation."""

    name: str
    value: Decimal
    metadata: dict[str, Any]


class MultiTimeframeSnapshotData(TypedDict):
    """Multi-timeframe snapshot for strategy engine."""

    timestamp_ms: int
    symbol: str
    candles: dict[str, ResampledCandleData]  # timeframe -> candle
    indicators: dict[str, dict[str, Decimal]]  # timeframe -> {indicator_name -> value}
    transforms: dict[str, Any]  # Additional computed transforms


# === Indicator Computation Types ===

IndicatorComputeFn = Callable[[Sequence[Decimal]], Decimal]
StreamingUpdateFn = Callable[[IndicatorStateData, Decimal], IndicatorStateData]


# === Candle Handler for Advanced Prep ===

CandleEmitFn = Callable[[str, ResampledCandleData], None]
MultiTimeframeReadyFn = Callable[[MultiTimeframeSnapshotData], None]


# === Backtesting Types ===

# Order types
OrderType = Literal["market", "limit", "stop", "stop_limit"]
OrderStatus = Literal["new", "partially_filled", "filled", "canceled", "rejected"]
TimeInForce = Literal["GTC", "IOC", "FOK", "DAY"]


class OrderData(TypedDict):
    """Order record for backtesting and live trading."""

    order_id: str
    symbol: str
    side: Side
    order_type: OrderType
    status: OrderStatus
    quantity: Decimal
    filled_quantity: Decimal
    limit_price: Decimal | None
    stop_price: Decimal | None
    time_in_force: TimeInForce
    submit_time_ms: int
    update_time_ms: int


class FillData(TypedDict):
    """Order fill event."""

    fill_id: str
    order_id: str
    symbol: str
    side: Side
    timestamp_ms: int
    price: Decimal
    quantity: Decimal
    fee: Decimal
    slippage: Decimal
    realized_pnl: Decimal | None


class PositionData(TypedDict):
    """Position state for a symbol."""

    symbol: str
    quantity: Decimal
    avg_entry_price: Decimal
    market_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal


class PortfolioStateData(TypedDict):
    """Portfolio state snapshot."""

    timestamp_ms: int
    cash: Decimal
    equity: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    positions: dict[str, PositionData]


class TradeLogEntryData(TypedDict):
    """Trade log entry for analysis."""

    trade_id: str
    order_id: str
    symbol: str
    side: Side
    timestamp_ms: int
    price: Decimal
    quantity: Decimal
    fee: Decimal
    slippage: Decimal
    realized_pnl: Decimal | None


class EquityPointData(TypedDict):
    """Equity curve data point."""

    timestamp_ms: int
    equity: Decimal
    cash: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal


class BacktestMetricsData(TypedDict):
    """Backtest performance metrics."""

    total_return: Decimal
    annualized_return: Decimal
    volatility: Decimal
    sharpe_ratio: Decimal
    max_drawdown: Decimal
    max_drawdown_duration_ms: int
    win_rate: Decimal
    avg_win: Decimal
    avg_loss: Decimal
    profit_factor: Decimal
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_trade_duration_ms: int
    exposure: Decimal
    turnover: Decimal


class BacktestResultData(TypedDict):
    """Complete backtest result."""

    config: dict[str, Any]
    metrics: BacktestMetricsData
    equity_curve: list[EquityPointData]
    positions: list[PositionData]
    trades: list[TradeLogEntryData]
    orders: list[OrderData]
    debug_traces: list[dict[str, Any]]


class BacktestConfigData(TypedDict, total=False):
    """Backtest configuration."""

    # General
    symbols: list[str]
    start_time_ms: int
    end_time_ms: int
    timeframe: str
    mode: Literal["event_driven", "vectorized"]
    initial_cash: Decimal
    base_currency: str

    # Execution model
    slippage_model: str  # "fixed_bps", "percentage", "spread_based", "custom"
    slippage_bps: Decimal
    commission_model: str  # "fixed", "percentage", "tiered"
    commission_rate: Decimal
    latency_ms: int
    order_matching: str  # "bar_based", "tick_based", "realistic"

    # Risk constraints
    max_leverage: Decimal
    max_position_size: Decimal
    max_notional: Decimal
    allow_short: bool

    # Logging and output
    record_equity_curve: bool
    record_positions: bool
    record_orders: bool
    record_trades: bool
    log_level: str
    random_seed: int


# Strategy callback types
StrategyContextData = dict[str, Any]  # Will be refined in implementation
OnStartFn = Callable[[StrategyContextData], None]
OnEndFn = Callable[[StrategyContextData], None]
OnBarFn = Callable[[StrategyContextData, CandleData], None]
OnTickFn = Callable[[StrategyContextData, TickData], None]
OnFillFn = Callable[[StrategyContextData, FillData], None]
OnOrderUpdateFn = Callable[[StrategyContextData, OrderData], None]


class StrategyInterfaceData(TypedDict, total=False):
    """Strategy interface with callbacks."""

    on_start: OnStartFn
    on_end: OnEndFn
    on_bar: OnBarFn
    on_tick: OnTickFn
    on_fill: OnFillFn
    on_order_update: OnOrderUpdateFn


# Slippage and commission function types
SlippageComputeFn = Callable[[OrderData, Decimal, Any], Decimal]
CommissionComputeFn = Callable[[OrderData, Decimal], Decimal]
