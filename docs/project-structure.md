# **Project Structure**

## **Overview**

This document defines a flat, extensible project structure for a trading application.  
The layout is intentionally shallow (1–3 levels) to keep navigation simple and ensure automation, refactoring, and
onboarding remain frictionless.

**Policy:** Documentation is generated only when explicitly requested, with clearly defined scope and format.

---

## **Related Documents**

- [AGENTS.md](/AGENTS.md) — comprehensive rules for AI agents
- [docs/naming-conventions.md](/docs/naming-conventions.md) — naming rules
- [.github/copilot-instructions.md](/.github/copilot-instructions.md) — quick reference

---

## **Core Principles**

1. **Flat hierarchy** — Prefer top-level domains with at most one nested level.
2. **Separation of concerns** — Ingestion, preparation, strategies, controllers, backtesting, UI, and backend are
   isolated modules.
3. **Typed contracts** — Use `TypedDict` for data schemas and `Callable` aliases for pluggable logic.
4. **Function-first architecture** — Favor pure functions and pipelines over classes and inheritance.
5. **Hot-path efficiency** — Use `dict`/`TypedDict` and dataclasses in performance-critical paths; validate external I/O
   at boundaries.
6. **Explicit dependency injection** — Pass providers, executors, and configuration into pipelines; avoid global mutable
   state.
7. **Extensibility** — Add new providers, strategies, or systems by adding modules under the appropriate top-level
   folder without modifying existing code.

---

## **Structure Levels**

- **Level 1:** Stable top-level folders representing major domains.
- **Level 2:** Optional subfolders grouping related implementations or variants.
- **Files:** Modules, types, and utilities placed inside domain folders with descriptive, domain-focused names.

---

## **Core Components and Responsibilities**

### **Data Controller**

**Purpose:** Coordinate data providers and manage ingestion, normalization, and unified delivery of market data.

**Responsibilities:**

- Connect to live exchanges and testnets (e.g., Binance Spot, Futures, Testnet).
- Provide unified interfaces for:
    - WebSocket tick streaming
    - REST-based historical retrieval
- Parse heterogeneous payloads into strongly typed, normalized structures.
- Handle reconnection, rate limits, backoff, and integrity checks (sequence gaps, timestamp drift, malformed payloads).
- Support both live streaming and historical replay with consistent output schemas.
- Enforce a unified data contract for downstream components (pipelines, indicators, strategies).
- Manage lifecycle: initialization, provider registration, teardown, and health monitoring.

---

### **Advanced Data Preparation**

**Purpose:** Produce enriched, multi-timeframe, and derived series for strategy consumption.

**Responsibilities:**

- Resample and align multiple timeframes.
- Compute indicators and transforms (Heiken Ashi, ATR, EMA, VWAP, etc.).
- Provide caching, rolling windows, and streaming helpers optimized for hot loops.

---

### **Pluggable Parameterized Strategies**

**Purpose:** Implement strategy logic as composable, parameterized pure functions.

**Responsibilities:**

- Expose a pure function accepting typed market data and parameters, returning signals/orders.
- Provide default parameter sets and a factory for creating configured strategy instances.
- Ensure strategies remain stateless; state is handled by controllers or pipelines.

---

### **Backtesting Controller**

**Purpose:** Execute deterministic historical simulations and produce metrics, logs, and traces.

**Responsibilities:**

- Replay market data and call strategy functions.
- Simulate fills, slippage, commissions, and execution latency.
- Produce equity curves, position series, and trade logs.
- Support vectorized or event-driven execution depending on performance needs.

---

### **Risk Controller**

**Purpose:** Enforce global account-level risk constraints around strategy output.

**Responsibilities:**

- Apply drawdown limits, max position sizing, exposure caps, and volatility-aware sizing.
- Monitor slippage and commission impact; adjust or block orders when thresholds are exceeded.
- Provide emergency stop hooks and risk alerts.

---

### **Backend Server**

**Purpose:** Provide paper/live trading endpoints, manage runtime state, and persist logs.

**Responsibilities:**

- Expose REST/WebSocket endpoints for control, telemetry, and order submission.
- Authenticate and isolate paper vs. live accounts.
- Persist trades, positions, configurations, and runtime logs.

---

### **Browser UI Client**

**Purpose:** Visualize backtests, live telemetry, and provide interactive controls.

**Responsibilities:**

- Display equity curves, trade lists, and per-trade analytics.
- Provide controls for starting/stopping strategies, adjusting parameters, and inspecting logs.
- Connect to backend for real-time updates and commands.

---

## **Example Layout**

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
