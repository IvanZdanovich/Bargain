### Backtesting controller – implementation prompt

**Goal:**  
Implement a **Backtesting Controller** that can run deterministic historical simulations of trading strategies and
produce metrics, logs, and traces. The same strategy code used in backtests **must** be usable in live trading without
modification (shared interfaces, no backtest-only hacks).

---

### 1. High-level requirements

- **Deterministic simulations:**
    - Given the same historical data, configuration, and random seed, results must be reproducible.
    - All sources of randomness (slippage models, order matching, etc.) must be seedable.

- **Real-strategy parity:**
    - The backtester must call the **same strategy interface** as live trading:
        - Same function signatures (e.g. `on_bar`, `on_tick`, `on_order_fill`, etc.).
        - Same order objects, position objects, and portfolio abstraction.
    - No branching like `if backtest: ... else: ...` inside strategy code. Environment differences should be abstracted
      behind interfaces.

- **Execution modes:**
    - **Event-driven mode:** iterate over events (ticks, trades, candles, order book updates) and feed them into the
      strategy.
    - **Vectorized mode:** for simple bar-based strategies, allow vectorized computation over arrays/frames for speed.
    - A single controller API should expose both modes via configuration.

- **Outputs:**
    - **Equity curve** over time.
    - **Position series** (per symbol, per timestamp).
    - **Trade log** (entries, exits, partial fills, fees, slippage).
    - **Order log** (submitted, canceled, rejected).
    - **Performance metrics** (e.g. PnL, drawdown, Sharpe, win rate, exposure, turnover).
    - **Debug traces** (optional, configurable verbosity).

---

### 2. Core abstractions and interfaces

Design the Backtesting Controller around clear, reusable interfaces. Use names that fit your codebase, but keep the
roles.

#### 2.1. Strategy interface

- **Required callbacks (example):**
    - `on_start(context)`
    - `on_bar(context, bar)` or `on_candle(context, candle)`
    - `on_tick(context, tick)` (optional if tick-level)
    - `on_order_fill(context, fill_event)`
    - `on_end(context)`

- **Strategy actions:**
    - Strategy should place orders via a **broker-like API** exposed in `context`, e.g.:
        - `context.broker.market_order(symbol, side, quantity)`
        - `context.broker.limit_order(symbol, side, quantity, price, time_in_force)`
        - `context.broker.cancel_order(order_id)`
    - Strategy should query state via:
        - `context.portfolio` (cash, equity, margin, positions).
        - `context.data` (historical bars, indicators, etc., if you support this).

- This interface must be **identical** between backtesting and live trading, with only the underlying implementation
  swapped.

#### 2.2. Market data interface

- **Input data types:**
    - Candles/bars (OHLCV).
    - Optional: trades, order book snapshots, or best bid/ask.
- **Data source abstraction:**
    - Implement a `MarketDataFeed` interface that:
        - Yields events in chronological order.
        - Can be configured for:
            - Symbol(s).
            - Time range.
            - Timeframe (e.g. 1m, 5m, 1h).
            - Event type (bars vs ticks).
- For vectorized mode, provide bulk access (e.g. arrays/dataframes) to the same underlying data.

#### 2.3. Broker/execution simulator

- Implement a `SimulatedBroker` that:
    - Accepts orders from the strategy.
    - Simulates:
        - **Fills** based on market data (bar or tick).
        - **Slippage** (configurable model).
        - **Commissions/fees** (configurable per exchange/symbol).
        - **Execution latency** (configurable, e.g. delay in events).
    - Maintains:
        - Open orders.
        - Positions.
        - Cash and equity.
    - Emits:
        - Fill events.
        - Order status updates.
- The broker interface should mirror the live broker/exchange adapter (e.g. Binance Spot), so strategies don’t care
  whether they’re in backtest or live.

---

### 3. Simulation engine

#### 3.1. Event-driven engine

- **Main loop:**
    1. Initialize `context`, `SimulatedBroker`, `MarketDataFeed`, and strategy.
    2. Call `strategy.on_start(context)`.
    3. For each event from `MarketDataFeed` in chronological order:
        - Update internal clock and context time.
        - Pass event to strategy (`on_bar` or `on_tick`).
        - Process any new orders submitted by strategy:
            - Send to `SimulatedBroker`.
            - Broker updates order book, fills, positions, cash.
            - Emit fill/order events back to strategy via `on_order_fill`.
        - Record state snapshots if needed (equity, positions, etc.).
    4. After all events, call `strategy.on_end(context)`.
    5. Finalize logs and metrics.

- **Determinism:**
    - Ensure event ordering is strictly defined.
    - Use a single RNG instance with a known seed for slippage and any stochastic models.

#### 3.2. Vectorized engine

- For strategies that can be expressed as pure functions over historical arrays:
    - Provide a `VectorizedBacktester` that:
        - Loads full historical data into arrays/dataframes.
        - Applies strategy logic in a vectorized manner (e.g. signals, positions, PnL).
        - Uses the same commission/slippage models but applied vector-wise.
    - Still produce:
        - Equity curve.
        - Position series.
        - Trade log (reconstructed from vectorized signals/positions).
- Keep the API consistent:
    - Same configuration object.
    - Same output structure as event-driven mode.

---

### 4. Configuration and parameters

Create a `BacktestConfig` structure/object with at least:

- **General:**
    - `symbols`: list of symbols.
    - `start_time`, `end_time`.
    - `timeframe` (for bar-based).
    - `mode`: `"event_driven"` or `"vectorized"`.
    - `initial_cash`.
    - `base_currency`.

- **Execution model:**
    - `slippage_model` (e.g. fixed bps, percentage of spread, custom function).
    - `commission_model` (e.g. per-trade, per-volume, exchange-like fee schedule).
    - `latency_ms` or `latency_bars`.
    - `order_matching` rules (e.g. bar-based: use OHLC rules for fills).

- **Risk and constraints:**
    - `max_leverage`.
    - `max_position_size` per symbol.
    - `max_notional` per trade.
    - Margin rules if applicable.

- **Logging and output:**
    - `record_equity_curve` (bool).
    - `record_positions` (bool).
    - `record_orders` (bool).
    - `record_trades` (bool).
    - `log_level` (e.g. DEBUG/INFO/WARN).
    - `random_seed`.

---

### 5. Output data structures

Design outputs to be easy to analyze and to plug into reporting tools.

- **Equity curve:**
    - Time-indexed series with:
        - `timestamp`
        - `equity`
        - `cash`
        - `unrealized_pnl`
        - `realized_pnl`

- **Position series:**
    - For each symbol and timestamp:
        - `symbol`
        - `timestamp`
        - `quantity`
        - `avg_entry_price`
        - `market_value`

- **Trade log:**
    - One row per fill:
        - `trade_id`
        - `order_id`
        - `symbol`
        - `side` (buy/sell)
        - `timestamp`
        - `price`
        - `quantity`
        - `fee`
        - `slippage`
        - `realized_pnl` (if closing or partial closing)

- **Order log:**
    - `order_id`
    - `symbol`
    - `side`
    - `type` (market/limit/stop/etc.)
    - `status` (new, partially_filled, filled, canceled, rejected)
    - `submit_time`
    - `update_time`
    - `limit_price` (if applicable)
    - `time_in_force`

- **Metrics summary:**
    - `total_return`
    - `annualized_return`
    - `volatility`
    - `sharpe_ratio`
    - `max_drawdown`
    - `win_rate`
    - `avg_win`, `avg_loss`
    - `profit_factor`
    - `exposure` (time in market)
    - `turnover`

---

### 6. Integration with live trading

The Backtesting Controller must be designed so that:

- **Strategy code is shared:**
    - Same strategy class/module used in both backtesting and live trading.
- **Environment swap:**
    - Backtest uses:
        - `SimulatedBroker`
        - `MarketDataFeed` (historical)
    - Live uses:
        - `LiveBroker` (e.g. Binance Spot API adapter)
        - `LiveMarketDataFeed` (e.g. WebSocket streams)
- **Common context:**
    - `context` object has the same attributes in both environments:
        - `context.broker`
        - `context.portfolio`
        - `context.clock` or `context.now`
        - `context.config`
- This ensures that a strategy proven in backtests can be deployed to live trading **without code changes**, only by
  switching the environment wiring.

---

### 7. Logging, tracing, and debugging

- **Structured logging:**
    - Use structured logs (e.g. JSON or key-value) for:
        - Orders.
        - Trades.
        - Portfolio snapshots.
        - Errors and warnings.
- **Trace options:**
    - Configurable verbosity:
        - Minimal (only summary metrics).
        - Normal (orders + trades + equity).
        - Debug (per-event state, internal decisions).
- **Error handling:**
    - Fail fast on inconsistent states (e.g. negative cash beyond allowed margin).
    - Provide clear error messages with timestamps and event context.

---

### 8. Performance considerations

- **Event-driven:**
    - Efficient iteration over large datasets.
    - Avoid unnecessary object allocations in the hot loop.
    - Optionally support batching events per bar or per time slice.

- **Vectorized:**
    - Use array/dataframe operations where possible.
    - Minimize Python-level loops if using Python.

- **Scalability:**
    - Should handle:
        - Multiple symbols.
        - Multi-year historical data.
    - Provide progress reporting or hooks for long runs.

---

### 9. Deliverables

Implement:

1. **BacktestingController** (main entry point):
    - `run_backtest(strategy, config) -> BacktestResult`
2. **BacktestResult**:
    - Contains equity curve, position series, trade log, order log, metrics summary, and any debug traces.
3. **SimulatedBroker** and **MarketDataFeed** implementations.
4. Shared **strategy interface** and **context** used by both backtesting and live trading.

---
