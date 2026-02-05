# .github/copilot-instructions.md

## Purpose

Quick reference for code-generation agents. For complete rules, see [AGENTS.md](/AGENTS.md).

---

## Quick Rules

1. **No docs unless requested** — place any docs in `docs/`, require human review.
2. **Prefer functions over classes** — use dataclasses only for immutable records.
3. **Centralize types** — all `TypedDict` and `Callable` aliases in `src/types.py`.
4. **TypedDict naming** — suffix with `Data`, `DTO`, or `Record`.
5. **Callable naming** — suffix with `Fn` or `Handler`.
6. **Small pure functions** — compose pipelines, no side effects in strategies.
7. **No global mutable state** — pass dependencies explicitly.
8. **Include docstrings** — state input/output types and side effects.
9. **Add unit tests** — for each new function.
10. **Follow naming conventions** — see [docs/naming-conventions.md](/docs/naming-conventions.md).

---

## Repo Layout

```
src/
  types.py          — all TypedDicts and Callable aliases
  feeds/            — adapters and parsers
  prep/             — indicators and multitimeframe utilities
  strategies/       — strategy factories and default params
  backtest/         — runner and simulator
  risk/             — risk controller and metrics
  server/           — API and storage
ui/                 — frontend assets
tests/              — unit and integration tests
configs/            — YAML/TOML configs
RFCs/               — proposals for structural or rule changes
docs/               — documentation
```

---

## PR Checklist

See [AGENTS.md](/AGENTS.md) for full checklist. Summary:

- [ ] Types in `src/types.py`
- [ ] Parsers for external inputs
- [ ] No global mutable state
- [ ] Unit tests added
- [ ] `mypy --strict` passes
- [ ] Docstrings present

