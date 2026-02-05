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
