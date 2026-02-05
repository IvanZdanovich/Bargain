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

**Examples:**

- `feeds/binance.py` — live REST and websocket adapters
- `feeds/testnet.py` — testnet adapter
- `feeds/ingest.py` — unified ingestion API and parsers

---

### Advanced Data Preparation

**Purpose:** Produce enriched, multi-timeframe, and derived series for strategies.

**Responsibilities:**

- Resample and align multiple timeframes.
- Compute indicators and transforms such as Heiken Ashi, ATR, EMA, VWAP.
- Provide caching and windowed streaming helpers for hot loops.

**Examples:**

- `prep/multitimeframe.py` — resampling and alignment utilities
- `prep/indicators.py` — `heiken_ashi`, `atr`, `ema` functions

---

### Pluggable Parameterized Strategies

**Purpose:** Strategy logic implemented as composable, parameterized functions.

**Responsibilities:**

- Expose a small pure function that accepts typed market data and parameters and returns signals/orders.
- Provide default parameter sets and a factory to create configured strategy functions.

**Examples:**

- `strategies/simple_momentum.py` — strategy factory and default params
- `strategies/params.yaml` — optional parameter presets

---

### Backtesting Controller

**Purpose:** Run historical simulations deterministically and produce metrics and traces.

**Responsibilities:**

- Replay market data, call strategy functions, simulate fills, slippage, and commissions.
- Produce time series of equity, positions, and trade logs.
- Support vectorized or event-driven backtests depending on performance needs.

**Examples:**

- `backtest/runner.py` — orchestrates replay and records results
- `backtest/simulator.py` — fill model and slippage logic

---

### Risk Controller

**Purpose:** Global account risk management wrapper around strategies.

**Responsibilities:**

- Enforce drawdown limits, max position sizing, exposure caps, and volatility-aware sizing.
- Monitor slippage and commission impact and adjust orders or pause strategies.
- Provide hooks for emergency stop and risk alerts.

**Examples:**

- `risk/controller.py` — risk enforcement and policy functions
- `risk/metrics.py` — drawdown, VaR, exposure calculators

---

### Backend Server

**Purpose:** Serve paper trading and live trading endpoints, manage state, and persist logs.

**Responsibilities:**

- Provide REST or WebSocket endpoints for control, telemetry, and order submission.
- Authenticate and isolate paper vs live accounts.
- Persist trade logs, positions, and configuration.

**Examples:**

- `server/app.py` — minimal FastAPI or Flask app
- `server/storage.py` — persistence layer (lightweight DB or files)

---

### Browser UI Client

**Purpose:** Visualize backtest results, live telemetry, and provide control surfaces.

**Responsibilities:**

- Display equity curves, trade lists, and per-trade analytics.
- Provide controls to start/stop strategies, change parameters, and inspect logs.
- Connect to backend for live updates and control commands.

**Examples:**

- `ui/` — static frontend built with a lightweight framework (React, Svelte, or plain HTML+JS)
- `ui/static/` — charts and visualization assets

---

## Naming Conventions Summary

See [docs/naming-conventions.md](/docs/naming-conventions.md) for full details.

| Element   | Convention                              | Examples                              |
|-----------|-----------------------------------------|---------------------------------------|
| Folders   | `snake_case`                            | `feeds/`, `prep/`, `strategies/`      |
| Files     | `snake_case`                            | `ingest.py`, `heiken_ashi.py`         |
| TypedDict | `PascalCase` + `Data`/`DTO`/`Record`    | `MarketTickData`, `OrderDTO`          |
| Callable  | `PascalCase` + `Fn`/`Handler`           | `PriceProviderFn`, `OrderExecutorFn`  |
| Functions | `snake_case` verb                       | `parse_tick`, `compute_atr`           |
| Constants | `UPPER_SNAKE_CASE`                      | `MAX_POSITION_SIZE`                   |
| Config    | YAML or TOML in `configs/`              | `configs/default.yaml`                |

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

---

## Extension Guidelines

1. **Add new providers** under `feeds/` with a single adapter module and a parse function that returns a typed shape.
2. **Add new strategies** under `strategies/` as small modules exposing a factory and default params.
3. **Add new indicators** under `prep/` as pure functions that accept and return typed series.
4. **Keep CI strict:** Add `mypy` or `pyright` checks and unit tests for any new module.
5. **Document only when requested:** If a design doc or user guide is needed, create a dedicated markdown file and add
   it to `docs/` only after explicit request.
6. **Propose structural changes** via RFC in `RFCs/` folder (see [AGENTS.md](/AGENTS.md)).

---

## Notes

- This structure is intended to be stable yet flexible.
- Keep modules small and focused to make automated generation and static checking straightforward.
- Validate all external inputs at the ingestion layer and convert to `TypedDict` before entering hot paths.
