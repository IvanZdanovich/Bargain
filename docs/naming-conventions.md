# Naming Conventions

This document consolidates naming rules for all code and files in the repository.

---

## Modules and Files

- Use `snake_case` for all module and file names.
- Examples: `market_ingest.py`, `risk_controller.py`, `heiken_ashi.py`.

---

## Types (TypedDict)

- Use `PascalCase` with suffix `Data`, `DTO`, or `Record`.
- Examples: `MarketTickData`, `OrderDTO`, `TradeRecord`.

---

## Callable Aliases

- Use `PascalCase` with suffix `Fn` or `Handler`.
- Examples: `PriceProviderFn`, `OrderExecutorFn`, `RiskModelFn`.

---

## Functions

- Use `snake_case` starting with a verb.
- Examples: `parse_tick`, `compute_atr`, `run_backtest`.

---

## Variables

- Use `snake_case`, descriptive names.
- Examples: `current_price`, `order_count`, `risk_limit`.

---

## Constants

- Use `UPPER_SNAKE_CASE`.
- Examples: `MAX_POSITION_SIZE`, `DEFAULT_TIMEOUT`, `API_BASE_URL`.

---

## Folders

- Use `snake_case` for top-level folders reflecting domain.
- Examples: `feeds/`, `prep/`, `strategies/`, `backtest/`, `risk/`, `server/`, `tests/`.

---

## Config Files

- Use YAML or TOML format.
- Place in `configs/` folder.
- Examples: `configs/default.yaml`, `configs/backtest.toml`.

---

## Tests

- Mirror module structure under `tests/`.
- Use `test_` prefix for test files.
- Examples: `tests/test_ingest.py`, `tests/test_backtest.py`.
