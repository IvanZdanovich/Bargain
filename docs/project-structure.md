# Project Structure

## Overview

This file defines a flat, extensible project structure for a trading application.
Keep the layout shallow (1–3 levels) so navigation and automation remain simple.

**Policy:** Do not generate documentation unless explicitly requested. Any docs must be created only when the user asks
and specifies scope and format.

---

## Related Documents

- [AGENTS.md](/AGENTS.md) — comprehensive rules for AI agents
- [docs/naming-conventions.md](/docs/naming-conventions.md) — naming rules
- [.github/copilot-instructions.md](/.github/copilot-instructions.md) — quick reference

---

## Principles

1. **Flat hierarchy:** Prefer top-level folders and at most one nested level for related files.
2. **Separation of concerns:** Data ingestion, data preparation, strategies, controllers, backtesting, UI, and backend
   are distinct modules.
3. **Typed contracts:** Use `TypedDict` for data shapes and `Callable` aliases for pluggable behavior.
4. **Function first:** Prefer small pure functions and pipelines over heavy class hierarchies.
5. **Hot path efficiency:** Use plain `dict`/`TypedDict` and dataclasses for performance-critical code; validate
   external I/O at boundaries.
6. **Explicit dependency injection:** Pass providers and executors into pipeline functions; avoid global mutable state.
7. **Extensible by design:** Add new providers, strategies, or systems by adding modules under the appropriate top-level
   folder.

---

## Structure Levels

- **Level 1:** Top-level folders that represent major domains. Keep this list short and stable.
- **Level 2:** Optional subfolders for related implementations or variants. Limit to one nested level.
- **Files:** Place modules, types, and small utilities inside folders. Keep file names descriptive and domain-focused.

---

## Core Components and Responsibilities

### Data Controller

**Purpose:** Manage data providers and initial ingestion and normalization.

**Responsibilities:**

- Connect to live exchanges and testnets (e.g., Binance API and Binance Testnet).
- Provide unified raw tick and historical fetch interfaces.
- Convert raw payloads into typed shapes via parse functions.

---

### Advanced Data Preparation

**Purpose:** Produce enriched, multi-timeframe, and derived series for strategies.

**Responsibilities:**

- Resample and align multiple timeframes.
- Compute indicators and transforms such as Heiken Ashi, ATR, EMA, VWAP.
- Provide caching and windowed streaming helpers for hot loops.

---

### Pluggable Parameterized Strategies

**Purpose:** Strategy logic implemented as composable, parameterized functions.

**Responsibilities:**

- Expose a small pure function that accepts typed market data and parameters and returns signals/orders.
- Provide default parameter sets and a factory to create configured strategy functions.

---

### Backtesting Controller

**Purpose:** Run historical simulations deterministically and produce metrics and traces.

**Responsibilities:**

- Replay market data, call strategy functions, simulate fills, slippage, and commissions.
- Produce time series of equity, positions, and trade logs.
- Support vectorized or event-driven backtests depending on performance needs.

---

### Risk Controller

**Purpose:** Global account risk management wrapper around strategies.

**Responsibilities:**

- Enforce drawdown limits, max position sizing, exposure caps, and volatility-aware sizing.
- Monitor slippage and commission impact and adjust orders or pause strategies.
- Provide hooks for emergency stop and risk alerts.

---

### Backend Server

**Purpose:** Serve paper trading and live trading endpoints, manage state, and persist logs.

**Responsibilities:**

- Provide REST or WebSocket endpoints for control, telemetry, and order submission.
- Authenticate and isolate paper vs live accounts.
- Persist trade logs, positions, and configuration.

---

### Browser UI Client

**Purpose:** Visualize backtest results, live telemetry, and provide control surfaces.

**Responsibilities:**

- Display equity curves, trade lists, and per-trade analytics.
- Provide controls to start/stop strategies, change parameters, and inspect logs.
- Connect to backend for live updates and control commands.

---

## Example Layout

```
src/
  types.py
  feeds/
    binance.py
    testnet.py
    ingest.py
  prep/
    multitimeframe.py
    indicators.py
  strategies/
    simple_momentum.py
    factory.py
  backtest/
    runner.py
    simulator.py
  risk/
    controller.py
    metrics.py
  server/
    app.py
    storage.py
ui/
  static/
  app.html
configs/
  default.yaml
tests/
  test_ingest.py
  test_backtest.py
RFCs/
docs/
mypy.ini
pyrightconfig.json
README.md
```
