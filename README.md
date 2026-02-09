# Bargain

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

The Advanced Data Preparation subsystem transforms raw, normalized market data into enriched, multi-timeframe, and feature-rich series optimized for strategy execution. It bridges the Data Controller and the Strategy Engine, ensuring downstream components receive clean, aligned, and computationally efficient data.

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

# Or without auto-fixing
black --check src tests && ruff check src tests && flake8 src tests && mypy src tests && pytest
```
