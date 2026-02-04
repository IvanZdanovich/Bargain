## Overview

This document defines minimal, actionable rules for AI agents that generate or modify code for a trading application.
Follow these rules to produce code that is **type safe**, **class minimal**, **fast in hot paths**, and **easy to extend
**. Use `TypedDict` for data shapes, `Callable` type aliases for pluggable behavior, and compose small pure functions
into typed pipelines. Validate external I/O at boundaries.

**Do not generate documentation unless explicitly requested.** Any request to produce docs must be explicit in the user
prompt.

---

## TypedDict Rules

- **Use TypedDict for every external or shared data shape.**
    - Enforces key names and types with zero runtime overhead.
- **Keep TypedDicts shallow and explicit.**
    - Prefer flat fields; if nested, name the nested TypedDict and reuse it.
- **Mark optional keys explicitly.**
    - Use `class X(TypedDict, total=False): ...`
- **Name TypedDicts as nouns ending with Data or DTO.**
    - Examples: `MarketTickData`, `OrderDTO`.
- **Provide a parsing function for each TypedDict.**
    - Pattern: `def parse_market_tick(raw: dict) -> MarketTickData: ...`
    - Purpose: convert and validate raw input before it enters pipelines.
- **Do not use TypedDict for behavior.**
    - Behavior contracts belong to Protocols or Callable aliases.

---

## Callable Rules

- **Define Callable type aliases for pluggable functions.**
    - Name pattern: VerbNoun ending with Fn or Handler.
    - Example: `PriceProviderFn = Callable[[str], float]`
- **Keep callables single responsibility and pure when possible.**
    - No side effects in strategy functions; side effects belong to executors.
- **Document expected exceptions and return semantics.**
    - Docstring should state whether `None` is allowed or exceptions are raised.
- **Provide default implementations and tests.**
    - Include a simple default function for examples and tests.

---

## Functional Pipeline Rules

- **Compose pipelines from small typed functions.**
    - Each function must have a single typed input and a single typed output.
- **Use explicit function names that describe transformation.**
    - Patterns: `ingest_raw_tick`, `normalize_tick`, `generate_signal`, `size_order`, `execute_order`.
- **Pass immutable records or TypedDicts between stages.**
    - Avoid mutating inputs; return new dicts or dataclasses.
- **Wire pluggable behavior via parameters, not global state.**
    - Example:
      `def run_pipeline(tick: MarketTickData, price_provider: PriceProviderFn, executor: ExecutorFn) -> ReportData:`
- **Type check the whole pipeline in CI.**
    - Tooling: enable `mypy --strict` or `pyright` and fail on type errors.
- **Add lightweight runtime assertions at stage boundaries.**
    - Catch mismatches that static checkers cannot see for external input.

---

## Runtime Validation and Hot Path Rules

- **Validate only at I/O boundaries.**
    - Where: websocket/parsers, REST responses, user input.
- **Use lightweight validators for hot paths.**
    - Minimal checks (presence and type) in hot loops; full validation at ingestion.
- **Prefer dict/TypedDict in hot loops.**
    - Minimal allocation and attribute lookup overhead.
- **Use pydantic or explicit parsing for external inputs.**
    - Convert validated pydantic models into TypedDicts before entering hot paths.
- **Avoid runtime reflection and heavy introspection in hot code.**

---

## Naming Conventions Rules

- **Files and modules:** `snake_case` and reflect domain area.
- **TypedDict and dataclass types:** `PascalCase` and end with `Data`, `DTO`, or `Record`.
- **Callable type aliases:** `PascalCase` and end with `Fn` or `Handler`.
- **Functions:** `snake_case` and start with a verb describing action.
- **Variables:** `snake_case` and be descriptive; avoid single-letter names except in short loops.
- **Constants:** `UPPER_SNAKE_CASE`.
- **Tests:** mirror module names and use `test_` prefix for functions.
- **Directories:** group by domain, not by pattern.

---

## Quick Decision Table

| Approach                               | When to use                                       | Runtime cost | Static guarantees                              |
|----------------------------------------|---------------------------------------------------|-------------:|------------------------------------------------|
| **TypedDict data contracts**           | Structured messages, ECS components, market ticks |          Low | Strong with mypy/pyright                       |
| **Function based interfaces**          | Pluggable strategies, risk models, executors      |   Negligible | Signature checked by static type checkers      |
| **Functional pipelines and contracts** | Composable systems, event driven flows            |          Low | End to end type flow; catches mismatches early |

---

## CI and Tooling Rules

- **Enable strict static checking** in CI (`mypy --strict` or `pyright` strict mode).
- **Fail the build** on type errors.
- **Run unit tests** for each pluggable function and pipeline stage.
- **Run lightweight runtime validation tests** for I/O parsers.
- **Document public TypedDicts and Callables** in a single reference file `types.py`.

---

## Tone and Style

- Clear and explicit over clever and compact.
- Prefer readability: short functions, clear names, one responsibility per function.
- Include short examples in docstrings showing how to call functions.
