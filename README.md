# Bargain

High-performance trading framework with unified market data ingestion, advanced data preparation, and deterministic
backtesting.

---

# Data Controller — Implementation Summary

## Module Structure

```
src/
├── types.py                     # All TypedDict and Callable aliases
├── data_controller/
│   ├── __init__.py              # Public API exports
│   ├── controller.py            # Main orchestrator
│   ├── event_bus.py             # Pub/sub event system
│   ├── normalization.py         # Pure parsing/validation functions
│   ├── reliability.py           # Retry, rate limiting, circuit breaker
│   ├── replay.py                # Replay mode for backtesting
│   ├── storage.py               # Storage layer integration
│   └── providers/
│       ├── __init__.py
│       └── binance.py           # Binance WebSocket/REST implementation
tests/
├── data_controller/
│   ├── test_normalization.py    # 51 tests
│   ├── test_binance.py          # 10 tests
│   ├── test_event_bus.py        # 15 tests
│   ├── test_reliability.py      # 18 tests
│   ├── test_controller.py       # 9 tests
│   ├── test_replay.py           # 9 tests
│   └── fixtures/sample_messages.jsonl
examples/
├── live_tick_ingestion.py       # Live streaming example
├── historical_candle_fetch.py   # Historical data example
├── event_bus_integration.py     # Strategy/storage integration
└── replay_backtest.py           # Replay mode example
```

## **Key Features Implemented**

### **Provider Abstraction Layer**

- Unified provider interface
- Binance Spot & Testnet support
- WebSocket streaming + REST historical fetch
- Pure parsing functions for:
    - trades
    - candles
    - order books
    - ticks

---

### **Data Normalization**

- Symbol normalization (`BTCUSDT → BTC/USDT`)
- Side normalization (`buy/sell`)
- Timestamp and sequence validation
- Order book integrity checks

---

### **Error Handling & Reliability**

- Exponential backoff retry
- Token‑bucket rate limiting
- Circuit breaker pattern
- Automatic reconnection

---

### **Event Bus Integration**

- Sync & async subscribers
- Decoupled event delivery
- Strategy component integration

---

### **Storage Layer**

- Buffered async writes
- Batch operations
- Configurable flush intervals

---

### **Modes of Operation**

- **Live streaming mode**
- **Historical batch mode**
- **Replay mode for backtesting**

---

# Advanced Data Preparation Subsystem

## Overview

The Advanced Data Preparation subsystem transforms raw, normalized market data into enriched, multi-timeframe, and
feature-rich series optimized for strategy execution. It bridges the Data Controller and the Strategy Engine, ensuring
downstream components receive clean, aligned, and computationally efficient data.

## Features

- **Multi-timeframe resampling**: Tick → 1s → 1m → 5m → 1h → 1d
- **Technical indicators**: EMA, SMA, WMA, VWAP, ATR, volatility measures
- **Transforms**: Heiken Ashi, log returns, percentage returns, normalization
- **Rolling windows**: O(1) append with efficient statistics computation
- **Streaming support**: Incremental updates optimized for hot loops
- **Deterministic behavior**: Identical results across live, batch, and replay modes

## Architecture

### Module Structure

```
src/advanced_prep/
├── __init__.py          # Public API exports
├── pipelines.py         # Multi-timeframe orchestration
├── resampling.py        # Tick → candle aggregation
├── indicators.py        # EMA, ATR, VWAP, etc.
├── transforms.py        # Heiken Ashi, returns, normalization
├── rolling.py           # Rolling windows, caches, ring buffers
├── state.py             # Stateful streaming helpers
├── registry.py          # Indicator registration & metadata
└── utils.py             # Shared helpers
```

### Data Flow

```
Data Controller → Normalized Ticks → Advanced Prep → Strategy Engine
                                    ↓
                          Multi-Timeframe Pipeline
                                    ↓
                    ┌───────────────┴───────────────┐
                    ↓                               ↓
              Resampling                       Indicators
                    ↓                               ↓
            OHLCV Candles                     EMA, ATR, etc.
                    ↓                               ↓
              Transforms                      Rolling Stats
                    ↓                               ↓
              Heiken Ashi                     Multi-TF Snapshot
```

---

# Backtesting Controller

## Overview

The Backtesting Controller enables deterministic historical simulation of trading strategies with realistic execution modeling. The same strategy code works identically in both backtesting and live trading environments.

## Key Features

- ✅ **Deterministic simulations** - Same data + config + seed = identical results
- ✅ **Event-driven engine** - Process market events chronologically with realistic timing
- ✅ **Realistic execution** - Configurable slippage, commissions, and latency
- ✅ **Strategy/live parity** - Identical interfaces for backtest and live modes
- ✅ **Comprehensive metrics** - Returns, Sharpe ratio, drawdown, win rate, profit factor
- ✅ **Complete audit trail** - Order log, trade log, equity curve, position tracking

## Module Structure

```
src/backtesting/
├── __init__.py          # Public API
├── controller.py        # Main backtest engine
├── strategy.py          # Strategy base class and context
├── broker.py            # Simulated broker and execution
├── feed.py              # Market data feed
├── clock.py             # Simulation clock and portfolio accessor
└── metrics.py           # Performance metrics computation

examples/
├── simple_backtest.py   # Basic momentum strategy
└── rsi_backtest.py      # RSI mean reversion with risk management

tests/backtesting/
├── test_broker.py       # Broker tests (18 tests passing)
├── test_controller.py   # Integration tests (3 tests passing)
└── test_metrics.py      # Metrics tests (21 tests passing)
```

## Quick Example

```python
from decimal import Decimal
from src.backtesting import run_backtest, StrategyBase, StrategyContext
from src.types import CandleData, BacktestConfigData

class RSIStrategy(StrategyBase):
    def on_bar(self, context: StrategyContext, bar: CandleData) -> None:
        rsi = compute_rsi(self.prices)
        if rsi < 30:  # Oversold
            qty = context.portfolio.cash * Decimal("0.2") / bar["close"]
            context.broker.market_order(bar["symbol"], "buy", qty, bar["open_time_ms"])

config: BacktestConfigData = {
    "symbols": ["BTC/USDT"],
    "initial_cash": Decimal("10000"),
    "commission_rate": Decimal("0.001"),
    "random_seed": 42,
}

result = run_backtest(RSIStrategy(), feed, config)
print(f"Return: {float(result['metrics']['total_return']) * 100:.2f}%")
print(f"Sharpe: {float(result['metrics']['sharpe_ratio']):.2f}")
```

## Strategy Interface

```python
class MyStrategy(StrategyBase):
    def on_start(self, context: StrategyContext) -> None:
        # Initialize strategy state
        self.position = Decimal("0")
    
    def on_bar(self, context: StrategyContext, bar: CandleData) -> None:
        # Process each bar and generate signals
        if should_buy():
            context.broker.market_order(symbol, "buy", quantity, timestamp)
    
    def on_fill(self, context: StrategyContext, fill: FillData) -> None:
        # Handle order fills
        logger.info(f"Filled: {fill['quantity']} @ {fill['price']}")
```

## Broker API

```python
# Place orders
context.broker.market_order(symbol, side, quantity, timestamp)
context.broker.limit_order(symbol, side, quantity, limit_price, timestamp)
context.broker.cancel_order(order_id, timestamp)

# Query portfolio
cash = context.portfolio.cash
equity = context.portfolio.equity
position = context.portfolio.get_position(symbol)
has_position = context.portfolio.has_position(symbol)
```

## Performance Metrics

The backtest result includes:
- **Returns**: Total, annualized, volatility
- **Risk-adjusted**: Sharpe ratio, max drawdown (with duration)
- **Trade statistics**: Win rate, profit factor, avg win/loss
- **Logs**: Equity curve, positions, orders, trades with realized PnL

## Documentation

See [docs/backtesting-guide.md](docs/backtesting-guide.md) for complete documentation.

---

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_module.py

# Run tests with verbose output
pytest -v
```

### Linting

```bash
# Check code with ruff (fast, comprehensive)
ruff check src tests

# Auto-fix ruff issues
ruff check --fix src tests

# Check code with flake8
flake8 src tests


# Type checking with mypy
mypy src tests
```

### Formatting

```bash
# Format code with black
black src tests

# Check formatting without changes
black --check src tests
```

### All Checks

```bash
# Run all quality checks at once (with auto-fix)
ruff check --fix src tests && black src tests && flake8 src tests && mypy src tests && pytest
```

```bash
# Or without auto-fixing
black --check src tests && ruff check src tests && flake8 src tests && mypy src tests && pytest
```
